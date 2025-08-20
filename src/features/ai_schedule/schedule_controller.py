from __future__ import annotations

import os
import json
from typing import Any, Optional

from src.utils.load_documents import load_document, crawler_roadmap_to_docs
from src.utils.vector_store import load_vector_store, create_vector_store
from src.utils.custom_emb import create_embeddings
from src.utils.initialize_llms import initialize_llm
from src.utils.create_agent import create_agent
from src.utils.learning_path import create_learning_path
from langchain.memory import ConversationBufferMemory


def _get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy biến môi trường theo thứ tự:
      1) os.environ (Render/Railway/Heroku…)
      2) .env (nếu có python-dotenv và file tồn tại)
      3) default
    """
    if key in os.environ:
        return os.environ.get(key)

    try:
        from dotenv import dotenv_values  # optional
        vals = dotenv_values(".env")
        if key in vals and vals[key]:
            return vals[key]
    except Exception:
        pass

    return default


def _get(req: Any, name: str, default: Any = None) -> Any:
    """Lấy thuộc tính từ req (hỗ trợ cả object và dict)."""
    if isinstance(req, dict):
        return req.get(name, default)
    return getattr(req, name, default)


def GenSchedule(req: Any, roadmap_data=None):
    try:
        # --- Load documents ---
        documents = crawler_roadmap_to_docs(roadmap_data)
        if not documents:
            return "No documents found to load."

        # --- Embeddings + Vector Store ---
        embeddings = create_embeddings()

        # Ưu tiên ENV → .env → mặc định
        vectordb_path = _get_env_var("VECTORDB_PATH", "./chroma_db")

        # Nếu thư mục đã tồn tại → load, ngược lại → tạo mới
        if vectordb_path and os.path.exists(vectordb_path):
            vector_store = load_vector_store(db_path=vectordb_path, embeddings=embeddings)
        else:
            vector_store = create_vector_store(documents, embeddings, db_path=vectordb_path)

        # --- LLM, Agent ---
        # Cho phép override loại LLM qua ENV LLM_TYPE (vd: "groq", "openai", "gemini", "local")
        llm_type = _get_env_var("LLM_TYPE", "gemini")
        llm = initialize_llm(llm_type=llm_type)
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # --- Create learning path ---
        learning_goal = _get(req, "query", "")
        user_knowledge = _get(req, "level", "")
        deadline = _get(req, "deadline", "")

        # Hàm create_learning_path của bạn có thể là (agent, goal, user_knowledge) hoặc có thêm deadline.
        # Nếu version của bạn CHƯA nhận deadline, chỉ cần bỏ tham số đó.
        try:
            learning_path = create_learning_path(agent, learning_goal, deadline, user_knowledge)
        except TypeError:
            # fallback cho phiên bản cũ chỉ có (agent, learning_goal, user_knowledge="")
            learning_path = create_learning_path(agent, learning_goal, user_knowledge)

        if not learning_path:
            return "LLM returned empty learning path."

        # ✅ Trả về câu trả lời gốc từ LLM/Agent (không ép JSON)
        return learning_path

    except Exception as e:
        return f"Error: {str(e)}"
