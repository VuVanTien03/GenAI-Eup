from __future__ import annotations

import os
import time
import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from datetime import datetime, timezone

# Features
from src.features.ai_schedule.schedule_controller import GenSchedule
from src.constant.ScheduleType import Schedule

# MongoDB
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Selenium for crawling
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------
# Helpers: env loader
# -----------------------------
def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy biến môi trường theo thứ tự:
      1) os.environ (Render/Railway/Heroku đặt ở đây)
      2) .env (nếu có python-dotenv và file tồn tại)
      3) default
    """
    if key in os.environ:
        return os.environ.get(key)
    try:
        from dotenv import dotenv_values  # optional import
        vals = dotenv_values(".env")
        if key in vals and vals[key]:
            return vals[key]
    except Exception:
        pass
    return default


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------
# App init
# -----------------------------
app = FastAPI(title="EUP AI Tutor", description="AI Tutor with Roadmap Crawler", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # chỉnh theo domain của bạn nếu cần
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------
# MongoDB connection
# -----------------------------
mongo_client: Optional[MongoClient] = None
db = None
roadmaps_collection = None
learning_path_collection = None

try:
    MONGODB_URI = get_env_var("MONGODB_URI")
    DATABASE_NAME = get_env_var("DATABASE_NAME", "eup_ai_tutor")

    if not MONGODB_URI:
        raise ValueError("Missing MONGODB_URI in environment or .env")

    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
    # Trigger server selection
    mongo_client.admin.command("ping")

    db = mongo_client[DATABASE_NAME]
    roadmaps_collection = db["roadmaps"]
    learning_path_collection = db["learning_path"]
    logger.info("✅ MongoDB connection established")
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    mongo_client = None


# -----------------------------
# Pydantic models
# -----------------------------
class RoadmapRequest(BaseModel):
    target: str
    level: Optional[str] = "beginner"
    force_crawl: Optional[bool] = False


class RoadmapResponse(BaseModel):
    success: bool
    message: str
    roadmap_id: Optional[str] = None
    data: Optional[dict] = None


# -----------------------------
# Selenium Crawler
# -----------------------------
class RoadmapCrawler:
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self) -> bool:
        """Setup Chrome/Chromium driver for crawling."""
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-web-security")
            options.add_argument("--ignore-ssl-errors")
            options.add_argument("--window-size=1280,800")

            # Render/Railway thường cung cấp đường dẫn tới binary qua biến môi trường
            chrome_bin = get_env_var("GOOGLE_CHROME_BIN") or get_env_var("CHROME_BIN")
            chromedriver_path = get_env_var("CHROMEDRIVER_PATH")

            if chrome_bin:
                options.binary_location = chrome_bin

            if chromedriver_path and os.path.exists(chromedriver_path):
                service = Service(executable_path=chromedriver_path)
            else:
                # Fallback: tự tải driver (có thể bị chặn ở môi trường build không có internet)
                service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            logger.error(f"❌ Error setting up driver: {e}")
            return False

    def login_roadmap(self) -> bool:
        """Login to roadmap.sh if credentials are provided."""
        # Dùng env → .env → None
        email = get_env_var("ROADMAP_EMAIL")
        password = get_env_var("ROADMAP_PASSWORD")

        if not email or not password:
            logger.info("⚠️ No roadmap credentials provided, using without login")
            return True

        try:
            self.driver.get("https://roadmap.sh/login")
            time.sleep(3)

            # NOTE: Các ID có vẻ động — giữ nguyên theo code của bạn.
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "form:«r9R3»"))
            )
            email_field.send_keys(email)

            password_field = self.driver.find_element(By.ID, "form:«r9R3H1»")
            password_field.send_keys(password + Keys.RETURN)
            time.sleep(5)

            logger.info("✅ Successfully logged in to roadmap.sh")
            return True
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False

    def crawl_roadmap(self, query: str):
        """Crawl roadmap data for a specific target."""
        try:
            self.driver.get("https://roadmap.sh/ai/roadmap")
            time.sleep(8)

            input_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "«R5155»"))
            )
            input_box.clear()
            input_box.send_keys(query)
            input_box.send_keys(Keys.RETURN)
            time.sleep(7)  # đợi AI gen

            roadmap_data = self.parse_roadmap_content()
            return {
                "target": roadmap_data["title"],
                "query": query,
                "data": roadmap_data,
                "crawled_at": utcnow_iso(),
                "source": "roadmap.sh"
            }
        except Exception as e:
            logger.error(f"❌ Error crawling roadmap: {e}")
            return None

    def parse_roadmap_content(self):
        """
        Parse roadmap theo phân cấp:
          title (Target) -> label (Skill) -> topic (Sub-skill) -> subtopic (Sub-sub-skill)
        """
        try:
            nodes = self.driver.find_elements(By.CSS_SELECTOR, "[data-type]")

            roadmap = {
                "title": None,
                "skills": []  # [{ "name": skill, "subskills": [{ "name": sub, "subsubskills": [...] }] }]
            }

            current_title: Optional[str] = None
            current_skill: Optional[str] = None  # label
            current_subskill: Optional[str] = None  # topic
            pending_subsub: list[str] = []  # subtopic đợi đến khi có topic

            PLACEHOLDER_SUBSKILL = "Khác"

            skills_index: dict[str, dict] = {}
            subskills_index: dict[tuple[str, str], dict] = {}

            def ensure_skill(name: str) -> dict:
                name = (name or "").strip() or "Untitled"
                obj = skills_index.get(name)
                if obj is None:
                    obj = {"name": name, "subskills": []}
                    skills_index[name] = obj
                    roadmap["skills"].append(obj)
                return obj

            def ensure_subskill(skill_name: Optional[str], sub_name: Optional[str]) -> dict:
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
                nonlocal pending_subsub
                if not pending_subsub:
                    return
                parent_skill = current_skill or (current_title or "Untitled")
                sub_obj = ensure_subskill(parent_skill, PLACEHOLDER_SUBSKILL)
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
                        flush_pending_to_placeholder()
                        current_title = text
                        roadmap["title"] = text
                        current_skill = None
                        current_subskill = None

                    elif dtype == "label":
                        flush_pending_to_placeholder()
                        current_skill = text
                        ensure_skill(current_skill)
                        current_subskill = None

                    elif dtype == "topic":
                        parent_skill = current_skill or (current_title or "Untitled")
                        ensure_skill(parent_skill)
                        sub_obj = ensure_subskill(parent_skill, text)
                        current_subskill = text

                        if pending_subsub:
                            for ss in pending_subsub:
                                if ss not in sub_obj["subsubskills"]:
                                    sub_obj["subsubskills"].append(ss)
                            pending_subsub = []

                    elif dtype == "subtopic":
                        if current_subskill:
                            parent_skill = current_skill or (current_title or "Untitled")
                            sub_obj = ensure_subskill(parent_skill, current_subskill)
                            if text not in sub_obj["subsubskills"]:
                                sub_obj["subsubskills"].append(text)
                        else:
                            pending_subsub.append(text)
                    else:
                        continue

                except Exception:
                    continue

            flush_pending_to_placeholder()
            return roadmap

        except Exception as e:
            logger.error(f"❌ Error parsing roadmap content: {e}")
            return {"title": None, "skills": [], "learning_path": []}

    def close(self):
        if self.driver:
            self.driver.quit()


# Global crawler instance
crawler: Optional[RoadmapCrawler] = None


def get_crawler() -> RoadmapCrawler:
    global crawler
    if crawler is None:
        crawler = RoadmapCrawler()
    return crawler


# -----------------------------
# Background task
# -----------------------------
async def crawl_and_save_roadmap(target: str, level: str = "beginner"):
    """Background task to crawl and save roadmap."""
    try:
        crawler_instance = get_crawler()
        crawler_instance.login_roadmap()

        roadmap_data = crawler_instance.crawl_roadmap(target)

        if roadmap_data and mongo_client:
            result = roadmaps_collection.insert_one({
                **roadmap_data,
                "level": level,
                "status": "completed"
            })
            logger.info(f"✅ Roadmap saved to MongoDB with ID: {result.inserted_id}")
            return roadmap_data['data']

        return None
    except Exception as e:
        logger.error(f"❌ Error in background crawling: {e}")
        return None


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"Hello": "World", "service": "EUP AI Tutor with Roadmap Crawler"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if mongo_client else "degraded",
        "mongodb_connected": mongo_client is not None,
        "timestamp": utcnow_iso(),
    }


@app.post("/crawl-roadmap", response_model=RoadmapResponse)
async def crawl_roadmap_endpoint(request: RoadmapRequest, background_tasks: BackgroundTasks):
    """Crawl roadmap data from roadmap.sh and save to MongoDB."""
    if not mongo_client:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    target = (request.target or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target cannot be empty")

    # Check existing unless force_crawl
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

    background_tasks.add_task(crawl_and_save_roadmap, target, request.level)
    return RoadmapResponse(
        success=True,
        message=f"Roadmap crawling started for '{target}'. Check status with GET /roadmap/{target}",
        roadmap_id=None
    )


@app.get("/roadmap/{target}")
async def get_roadmap(target: str, level: str = "beginner"):
    """Get roadmap data from MongoDB."""
    if not mongo_client:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    roadmap = roadmaps_collection.find_one({"target": target, "level": level})
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    roadmap["_id"] = str(roadmap["_id"])
    return {"success": True, "data": roadmap}


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
        result = GenSchedule(req, roadmap)

        # Chuẩn hóa tài liệu để lưu vào Mongo
        if isinstance(result, dict):
            if result.get("error"):
                raise HTTPException(status_code=500, detail=f"Schedule generation failed: {result.get('error')}")
            doc = {
                "type": "schedule",
                "format": "json",
                "query": query,
                "level": level,
                "roadmap": roadmap,
                "data": result,
                "created_at": utcnow_iso(),
                "source": "GenSchedule"
            }
            response_payload = {"data": result}

        elif isinstance(result, str):
            doc = {
                "type": "schedule",
                "format": "text",
                "query": query,
                "level": level,
                "roadmap": roadmap,
                "text": result,
                "created_at": utcnow_iso(),
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
        raise HTTPException(status_code=500, detail=f"Schedule generation failed: {str(e)}")


@app.delete("/roadmap/{target}")
async def delete_roadmap(target: str, level: str = "beginner"):
    """Delete a specific roadmap."""
    if not mongo_client:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    result = roadmaps_collection.delete_one({"target": target, "level": level})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    return {"success": True, "message": f"Roadmap for '{target}' deleted successfully"}


# Cleanup on shutdown
@app.on_event("shutdown")
def shutdown_event():
    global crawler
    if crawler:
        crawler.close()
    if mongo_client:
        mongo_client.close()
