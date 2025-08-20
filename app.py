from fastapi import FastAPI, HTTPException, BackgroundTasks
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware
from src.features.ai_schedule.schedule_controller import GenSchedule
from src.constant.ScheduleType import Schedule
from pydantic import BaseModel
import asyncio
from typing import Optional
import json
import os
from datetime import datetime

# MongoDB imports
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Selenium imports for crawling
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

config = dotenv_values(".env")

app = FastAPI(title="EUP AI Tutor", description="AI Tutor with Roadmap Crawler", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    mongo_client = MongoClient(config.get("MONGODB_URI"))
    db = mongo_client[config.get("DATABASE_NAME")]
    roadmaps_collection = db["roadmaps"]
    learning_path_collection = db['learning_path']
    print("✅ MongoDB connection established")
except ConnectionFailure:
    print("❌ MongoDB connection failed")
    mongo_client = None


# Pydantic models
class RoadmapRequest(BaseModel):
    target: str
    level: Optional[str] = "beginner"
    force_crawl: Optional[bool] = False


class RoadmapResponse(BaseModel):
    success: bool
    message: str
    roadmap_id: Optional[str] = None
    data: Optional[dict] = None


class RoadmapCrawler:
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver for crawling"""
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-web-security")
            options.add_argument("--ignore-ssl-errors")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False

    def login_roadmap(self):
        """Login to roadmap.sh if credentials are provided"""
        email = config.get("ROADMAP_EMAIL")
        password = config.get("ROADMAP_PASSWORD")

        if not email or not password:
            print("⚠️ No roadmap credentials provided, using without login")
            return True

        try:
            self.driver.get("https://roadmap.sh/login")
            time.sleep(3)

            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "form:«r9R3»"))
            )
            email_field.send_keys(email)

            password_field = self.driver.find_element(By.ID, "form:«r9R3H1»")
            password_field.send_keys(password + Keys.RETURN)
            time.sleep(5)

            print("✅ Successfully logged in to roadmap.sh")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False

    def crawl_roadmap(self, query: str):
        """Crawl roadmap data for a specific target"""
        try:
            # Navigate to AI roadmap generator
            self.driver.get("https://roadmap.sh/ai/roadmap")
            time.sleep(8)

            # Find and fill the input
            input_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "«R5155»"))
            )

            input_box.clear()
            input_box.send_keys(query)
            input_box.send_keys(Keys.RETURN)
            time.sleep(7)  # Wait for AI to generate roadmap

            # Parse the generated roadmap
            roadmap_data = self.parse_roadmap_content()

            return {
                "target": roadmap_data["title"],
                "query": query,
                "data": roadmap_data,
                "crawled_at": datetime.now(),
                "source": "roadmap.sh"
            }

        except Exception as e:
            print(f"❌ Error crawling roadmap: {e}")
            return None

    def parse_roadmap_content(self):
        """
        Parse roadmap theo phân cấp:
          title (Target) -> label (Skill) -> topic (Sub-skill) -> subtopic (Sub-sub-skill)

        Cải tiến:
          - Gắn subtopic đúng subskill ngay cả khi subtopic xuất hiện trước topic (dùng hàng đợi).
          - Khi chuyển sang label/title mới mà còn subtopic treo -> flush vào subskill 'Khác' của skill hiện hành.
          - Không trùng skill/subskill, giữ thứ tự xuất hiện.
          - Fallback hợp lý: nếu thiếu label, subskill gắn vào title hiện tại.
        """
        try:
            nodes = self.driver.find_elements(By.CSS_SELECTOR, "[data-type]")

            roadmap = {
                "title": None,
                "skills": []  # [{ "name": skill, "subskills": [{ "name": sub, "subsubskills": [...] }] }]
            }

            # Trạng thái hiện tại
            current_title: str | None = None
            current_skill: str | None = None  # label
            current_subskill: str | None = None  # topic
            pending_subsub: list[str] = []  # subtopic đợi đến khi có topic

            PLACEHOLDER_SUBSKILL = "Khác"

            # Chỉ mục chống trùng, vẫn giữ thứ tự bằng list thật
            skills_index: dict[str, dict] = {}  # skill_name -> skill_obj
            subskills_index: dict[tuple[str, str], dict] = {}  # (skill_name, subskill_name) -> sub_obj

            def ensure_skill(name: str) -> dict:
                """Lấy/tạo skill theo tên, đảm bảo có trong roadmap."""
                name = (name or "").strip() or "Untitled"
                obj = skills_index.get(name)
                if obj is None:
                    obj = {"name": name, "subskills": []}
                    skills_index[name] = obj
                    roadmap["skills"].append(obj)
                return obj

            def ensure_subskill(skill_name: str | None, sub_name: str | None) -> dict:
                """Lấy/tạo sub-skill thuộc skill_name."""
                skill_name = (skill_name or "").strip() or (current_title or "Untitled")
                sub_name = (sub_name or "").strip() or PLACEHOLDER_SUBSKILL
                key = (skill_name, sub_name)
                obj = subskills_index.get(key)
                if obj is None:
                    parent_skill = ensure_skill(skill_name)
                    obj = {"name": sub_name, "subsubskills": []}
                    parent_skill["subskills"].append(obj)
                    subskills_index[key] = obj
                return obj

            def flush_pending_to_placeholder():
                """Đổ các subtopic đang treo vào subskill 'Khác' của skill hiện tại (nếu có)."""
                nonlocal pending_subsub
                if not pending_subsub:
                    return
                parent_skill = current_skill or (current_title or "Untitled")
                sub_obj = ensure_subskill(parent_skill, PLACEHOLDER_SUBSKILL)
                # chèn không trùng
                for ss in pending_subsub:
                    if ss not in sub_obj["subsubskills"]:
                        sub_obj["subsubskills"].append(ss)
                pending_subsub = []

            for node in nodes:
                try:
                    text = (node.text or "").strip()
                    if not text:
                        continue

                    dtype = (node.get_attribute("data-type") or "").strip()
                    if not dtype:
                        continue

                    if dtype == "title":
                        # Trước khi đổi title, flush subtopic treo của skill hiện hành
                        flush_pending_to_placeholder()
                        current_title = text
                        roadmap["title"] = text
                        # reset ngữ cảnh con
                        current_skill = None
                        current_subskill = None

                    elif dtype == "label":
                        # Trước khi sang skill mới, flush subtopic treo về skill cũ
                        flush_pending_to_placeholder()
                        current_skill = text
                        ensure_skill(current_skill)
                        current_subskill = None

                    elif dtype == "topic":
                        # Sub-skill thuộc skill hiện hành; nếu chưa có skill -> gắn vào title
                        parent_skill = current_skill or (current_title or "Untitled")
                        ensure_skill(parent_skill)  # đảm bảo skill tồn tại
                        sub_obj = ensure_subskill(parent_skill, text)
                        current_subskill = text

                        # Nếu đang có subtopic treo, gắn vào subskill này
                        if pending_subsub:
                            for ss in pending_subsub:
                                if ss not in sub_obj["subsubskills"]:
                                    sub_obj["subsubskills"].append(ss)
                            pending_subsub = []

                    elif dtype == "subtopic":
                        # Nếu đã có topic hiện hành, gắn trực tiếp; nếu chưa, tạm treo
                        if current_subskill:
                            parent_skill = current_skill or (current_title or "Untitled")
                            sub_obj = ensure_subskill(parent_skill, current_subskill)
                            if text not in sub_obj["subsubskills"]:
                                sub_obj["subsubskills"].append(text)
                        else:
                            pending_subsub.append(text)

                    else:
                        # Kiểu không nằm trong mapping -> bỏ qua
                        continue

                except Exception:
                    # Bỏ qua node lỗi đơn lẻ
                    continue

            # Kết thúc vòng lặp: nếu còn subtopic treo, đổ vào placeholder của skill hiện hành (hoặc title)
            flush_pending_to_placeholder()

            return roadmap

        except Exception as e:
            print(f"❌ Error parsing roadmap content: {e}")
            return {"title": None, "skills": [], "learning_path": []}

    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()


# Global crawler instance
crawler = None


def get_crawler():
    global crawler
    if crawler is None:
        crawler = RoadmapCrawler()
    return crawler


async def crawl_and_save_roadmap(target: str, level: str = "beginner"):
    """Background task to crawl and save roadmap"""
    try:
        crawler_instance = get_crawler()

        # Login if needed
        crawler_instance.login_roadmap()

        # Crawl roadmap
        roadmap_data = crawler_instance.crawl_roadmap(target)

        if roadmap_data and mongo_client:
            # Save to MongoDB
            result = roadmaps_collection.insert_one({
                **roadmap_data,
                "level": level,
                "status": "completed"
            })

            print(f"✅ Roadmap saved to MongoDB with ID: {result.inserted_id}")
            return roadmap_data['data']

        return None
    except Exception as e:
        print(f"❌ Error in background crawling: {e}")
        return None


@app.get("/")
def root():
    return {"Hello": "World", "service": "EUP AI Tutor with Roadmap Crawler"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mongodb_connected": mongo_client is not None,
        "timestamp": datetime.now()
    }


@app.post("/crawl-roadmap", response_model=RoadmapResponse)
async def crawl_roadmap_endpoint(request: RoadmapRequest, background_tasks: BackgroundTasks):
    """
    Crawl roadmap data from roadmap.sh and save to MongoDB
    """
    try:
        if not mongo_client:
            raise HTTPException(status_code=500, detail="MongoDB not connected")

        target = request.target.strip()
        if not target:
            raise HTTPException(status_code=400, detail="Target cannot be empty")

        # Check if roadmap already exists (unless force_crawl is True)
        if not request.force_crawl:
            existing = roadmaps_collection.find_one({
                "target": target,
                "level": request.level
            })

            if existing:
                return RoadmapResponse(
                    success=True,
                    message="Roadmap already exists",
                    roadmap_id=str(existing["_id"]),
                    data=existing.get("data")
                )

        # Start background crawling task
        background_tasks.add_task(crawl_and_save_roadmap, target, request.level)

        return RoadmapResponse(
            success=True,
            message=f"Roadmap crawling started for '{target}'. Check status with GET /roadmap/{target}",
            roadmap_id=None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/roadmap/{target}")
async def get_roadmap(target: str, level: str = "beginner"):
    """
    Get roadmap data from MongoDB
    """
    try:
        if not mongo_client:
            raise HTTPException(status_code=500, detail="MongoDB not connected")

        roadmap = roadmaps_collection.find_one({
            "target": target,
            "level": level
        })

        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")

        # Convert ObjectId to string for JSON serialization
        roadmap["_id"] = str(roadmap["_id"])

        return {
            "success": True,
            "data": roadmap
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_schedule(req: Schedule):
    """Query: crawl roadmap if needed, then generate study schedule"""

    if not mongo_client:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    query = (req.query or "").strip()
    level = (req.level or "").strip()

    # Crawl (và/hoặc lấy từ DB) roadmap gốc
    roadmap = await crawl_and_save_roadmap(query, level)

    try:
        # Có thể trả về dict (JSON) hoặc str (raw text) tùy bạn cấu hình GenSchedule
        result = GenSchedule(req, roadmap)

        # Chuẩn hóa tài liệu để lưu vào Mongo
        if isinstance(result, dict):
            # Nếu dict nhưng là lỗi
            if result.get("error"):
                raise HTTPException(status_code=500, detail=f"Schedule generation failed: {result.get('error')}")
            doc = {
                "type": "schedule",
                "format": "json",
                "query": query,
                "level": level,
                "roadmap": roadmap,        # có thể thay bằng roadmap_id nếu bạn muốn
                "data": result,            # dữ liệu JSON sạch
                "created_at": datetime.now(),
                "source": "GenSchedule"
            }
            response_payload = {"data": result}

        elif isinstance(result, str):
            # Lưu nguyên văn trả lời
            doc = {
                "type": "schedule",
                "format": "text",
                "query": query,
                "level": level,
                "roadmap": roadmap,
                "text": result,            # câu trả lời thô
                "created_at": datetime.utcnow(),
                "source": "GenSchedule"
            }
            response_payload = {"text": result}

        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported result type from GenSchedule: {type(result)}"
            )

        inserted = learning_path_collection.insert_one(doc)
        return {
            "success": True,
            "inserted_id": str(inserted.inserted_id),
            "format": doc["format"],
            **response_payload
        }

    except HTTPException:
        raise
    except Exception as e:
        # Bắt mọi lỗi không ngờ tới (LLM init, DB, v.v.)
        raise HTTPException(status_code=500, detail=f"Schedule generation failed: {str(e)}")

@app.delete("/roadmap/{target}")
async def delete_roadmap(target: str, level: str = "beginner"):
    """
    Delete a specific roadmap
    """
    try:
        if not mongo_client:
            raise HTTPException(status_code=500, detail="MongoDB not connected")

        result = roadmaps_collection.delete_one({
            "target": target,
            "level": level
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Roadmap not found")

        return {
            "success": True,
            "message": f"Roadmap for '{target}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup on shutdown
@app.on_event("shutdown")
def shutdown_event():
    global crawler
    if crawler:
        crawler.close()
    if mongo_client:
        mongo_client.close()