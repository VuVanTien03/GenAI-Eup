from __future__ import annotations

from typing import List, Union, Optional, Sequence, Tuple
import os

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document  # fallback cho version cũ

from src.utils.custom_emb import create_embeddings

# --- Helper load config ---
def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy biến môi trường ưu tiên theo thứ tự:
    1. os.environ (Render, Railway... sẽ set ở đây)
    2. .env (nếu có)
    3. default (nếu có)
    """
    value = os.environ.get(key)
    if value:
        return value
    try:
        from dotenv import dotenv_values
        env_values = dotenv_values(".env")
        return env_values.get(key, default)
    except Exception:
        return default


# =========================
# Kiểm tra list Document
# =========================
def _is_document_list(items: Sequence) -> bool:
    return len(items) > 0 and isinstance(items[0], Document)


# =========================
# Tạo Vector Store
# =========================
def create_vector_store(
    texts: Union[List[str], List[Document]],
    embeddings: Optional[HuggingFaceEmbeddings] = None,
    db_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    persist: bool = True,
) -> Chroma:
    try:
        if embeddings is None:
            embeddings = create_embeddings()

        if db_path is None:
            db_path = get_env_var("VECTORDB_PATH", "./chroma_db")

        os.makedirs(db_path, exist_ok=True)

        if _is_document_list(texts):
            vector_store = Chroma.from_documents(
                texts, embedding=embeddings, persist_directory=db_path, collection_name=collection_name
            )
        else:
            vector_store = Chroma.from_texts(
                texts, embedding=embeddings, persist_directory=db_path, collection_name=collection_name
            )

        if persist:
            vector_store.persist()

        return vector_store
    except Exception as e:
        raise RuntimeError(f"Error creating vector store: {e}") from e


# =========================
# Load Vector Store
# =========================
def load_vector_store(
    db_path: Optional[str] = None,
    embeddings: Optional[HuggingFaceEmbeddings] = None,
    collection_name: Optional[str] = None,
) -> Chroma:
    try:
        if embeddings is None:
            embeddings = create_embeddings()

        if db_path is None:
            db_path = get_env_var("VECTORDB_PATH", "./chroma_db")

        if not os.path.isdir(db_path):
            raise FileNotFoundError(f"Vector DB path không tồn tại: {db_path}")

        return Chroma(
            persist_directory=db_path,
            embedding_function=embeddings,
            collection_name=collection_name,
        )
    except Exception as e:
        raise RuntimeError(f"Error loading vector store: {e}") from e


# =========================
# Truy vấn
# =========================
def get_similar_docs(
    query: str,
    vector_store: Chroma,
    k: int = 5,
    with_score: bool = False,
):
    try:
        if with_score:
            return vector_store.similarity_search_with_score(query, k=k)
        else:
            return vector_store.similarity_search(query, k=k)
    except Exception:
        return []  # Không raise để không vỡ luồng gọi
