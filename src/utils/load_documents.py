from __future__ import annotations

import os
import json
from typing import List, Union, Dict, Any

# LangChain (bản community tách riêng)
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    WebBaseLoader,
)

# YoutubeLoader có thể không có sẵn dependency → ta import an toàn
try:
    from langchain_community.document_loaders import YoutubeLoader
    _YOUTUBE_AVAILABLE = True
except Exception:
    YoutubeLoader = None  # type: ignore
    _YOUTUBE_AVAILABLE = False

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# dotenv: chỉ load khi .env tồn tại (tránh lỗi trên Render)
try:
    from dotenv import load_dotenv, dotenv_values
except Exception:
    load_dotenv = None
    dotenv_values = None


# ======= Config helper (ENV-first, fallback .env, rồi đến default) =======
def _init_config() -> Dict[str, Any]:
    """
    Ưu tiên lấy từ ENV (Render, Docker, CI...), nếu có .env thì load để chạy local,
    cuối cùng có giá trị mặc định an toàn.
    """
    # Local only: load .env nếu tồn tại
    if load_dotenv is not None and os.path.exists(".env"):
        load_dotenv()

    # Đọc từ ENV trước
    cfg: Dict[str, Any] = {
        "CHUNK_SIZE": os.getenv("CHUNK_SIZE"),
        "CHUNK_OVERLAP": os.getenv("CHUNK_OVERLAP"),
    }

    # Nếu vẫn thiếu, thử fallback từ .env (local)
    if dotenv_values is not None and os.path.exists(".env"):
        _env_dict = dotenv_values(".env") or {}
        cfg["CHUNK_SIZE"] = cfg["CHUNK_SIZE"] or _env_dict.get("CHUNK_SIZE")
        cfg["CHUNK_OVERLAP"] = cfg["CHUNK_OVERLAP"] or _env_dict.get("CHUNK_OVERLAP")

    # Giá trị mặc định an toàn
    # (Bạn có thể chỉnh tùy workload: 1000/150 khá phổ biến cho LLM retrieval)
    if not cfg["CHUNK_SIZE"]:
        cfg["CHUNK_SIZE"] = "1000"
    if not cfg["CHUNK_OVERLAP"]:
        cfg["CHUNK_OVERLAP"] = "150"

    return cfg


CONFIG = _init_config()


# ======= Document loaders =======
def load_document(file_path: str) -> List[Document]:
    """
    Load document từ đường dẫn file hoặc URL, hỗ trợ:
      - Text (.txt, .md, .json, …)
      - PDF
      - Web page (http/https)
      - YouTube (youtube.com / youtu.be) — nếu YoutubeLoader khả dụng
    Trả về danh sách Document đã được chunk.
    """
    try:
        # Chọn loader phù hợp
        loader = None
        url_like = file_path.startswith("http://") or file_path.startswith("https://")

        if url_like:
            # YouTube?
            if ("youtube.com" in file_path or "youtu.be" in file_path) and _YOUTUBE_AVAILABLE:
                loader = YoutubeLoader.from_url(file_path)
            else:
                loader = WebBaseLoader(file_path)
        else:
            # File cục bộ
            lower = file_path.lower()
            if lower.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            else:
                # TextLoader có thể đọc txt, md, json (nhưng json sẽ là raw text).
                # Nếu bạn muốn parse JSON, hãy viết loader riêng. Ở đây ta ưu tiên đơn giản.
                loader = TextLoader(file_path, encoding="utf-8")

        if loader is None:
            raise ValueError("Không tìm được loader phù hợp cho đường dẫn đã cung cấp.")

        # Load thô
        raw_docs = loader.load()

        # Chunk theo cấu hình (ENV-first)
        chunk_size = int(str(CONFIG["CHUNK_SIZE"]))
        chunk_overlap = int(str(CONFIG["CHUNK_OVERLAP"]))

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],  # giúp tách mềm mại hơn
        )
        chunks = text_splitter.split_documents(raw_docs)
        return chunks

    except Exception as e:
        # Không raise để không làm crash pipeline — trả list rỗng và log ra stderr
        print(f"[load_document] Error loading '{file_path}': {e}")
        return []


def load_roadmap_json(file_path: str) -> List[Document]:
    """
    Đọc file JSON có cấu trúc:
    [
      {
        "target": "string",
        "category": "string",
        "skills": [
          {
            "name": "Skill name",
            "subskills": [
              {"name": "Sub", "subsubskills": ["x", "y"]},
              ...
            ]
          },
          ...
        ]
      },
      ...
    ]
    Convert thành list[Document] (mỗi entry là 1 Document).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if not isinstance(json_data, list):
            raise ValueError("File roadmap JSON phải là một list các entry.")

        documents: List[Document] = []
        for entry in json_data:
            target = str(entry.get("target", "") or "")
            category = str(entry.get("category", "") or "")
            skill_blocks: List[str] = []

            for skill in entry.get("skills", []) or []:
                name = str(skill.get("name", "") or "")
                skill_text_lines = [f"Skill: {name}"]
                for sub in skill.get("subskills", []) or []:
                    sub_name = str(sub.get("name", "") or "")
                    sub_line = f"  Subskill: {sub_name}"
                    # subsubskills: list[str]
                    subsubs = sub.get("subsubskills", []) or []
                    if subsubs:
                        for s in subsubs:
                            sub_line += f"\n    - {str(s)}"
                    skill_text_lines.append(sub_line)
                skill_blocks.append("\n".join(skill_text_lines))

            full_text = (
                f"Target: {target}\n"
                f"Category: {category}\n\n" + "\n\n".join(skill_blocks)
            ).strip()

            documents.append(
                Document(
                    page_content=full_text,
                    metadata={"target": target, "category": category, "source": "roadmap.json"},
                )
            )

        return documents

    except Exception as e:
        print(f"[load_roadmap_json] Error: {e}")
        return []


def crawler_roadmap_to_docs(roadmap_data: Union[Dict, List[Dict]]) -> List[Document]:
    """
    Convert dữ liệu từ crawler (roadmap.sh) thành list[Document].

    Schema kỳ vọng (ví dụ):
    {
      "title": "AI Engineer Roadmap",
      "skills": [
        {"name": "Python", "subskills": ["Syntax", "OOP", "Data Structures"]},
        {"name": "Machine Learning", "subskills": ["Supervised", "Unsupervised"]}
      ],
      "learning_path": []  # optional
    }

    Có thể nhận 1 object hoặc list các object.
    """
    try:
        if isinstance(roadmap_data, dict):
            items: List[Dict] = [roadmap_data]
        elif isinstance(roadmap_data, list):
            items = roadmap_data
        else:
            raise ValueError("roadmap_data phải là dict hoặc list[dict].")

        docs: List[Document] = []
        for item in items:
            title = str(item.get("title", "") or "")
            skills = item.get("skills", []) or []
            lp = item.get("learning_path", []) or []

            blocks: List[str] = []
            for sk in skills:
                sk_name = str((sk or {}).get("name", "") or "")
                subskills = (sk or {}).get("subskills", []) or []
                # subskills từ crawler có thể là list[str]
                block_lines = [f"Skill: {sk_name}"]
                for ss in subskills:
                    block_lines.append(f"  - {str(ss)}")
                blocks.append("\n".join(block_lines))

            lp_text = ""
            if isinstance(lp, list) and lp:
                lp_lines = ["Learning Path:"]
                for step in lp:
                    if isinstance(step, dict):
                        w = step.get("week") or step.get("step") or "N/A"
                        obj = step.get("objective") or step.get("title") or ""
                        lp_lines.append(f"  Week/Step {w}: {obj}")
                    else:
                        lp_lines.append(f"  - {str(step)}")
                lp_text = "\n" + "\n".join(lp_lines)

            page = f"Target: {title}\n" + "\n\n".join(blocks) + lp_text
            docs.append(
                Document(
                    page_content=page,
                    metadata={"title": title, "source": "roadmap.sh"},
                )
            )

        # Chunk luôn theo config (giống load_document) để tái sử dụng downstream
        chunk_size = int(str(CONFIG["CHUNK_SIZE"]))
        chunk_overlap = int(str(CONFIG["CHUNK_OVERLAP"]))
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
        return splitter.split_documents(docs)

    except Exception as e:
        print(f"[crawler_roadmap_to_docs] Error: {e}")
        return []
