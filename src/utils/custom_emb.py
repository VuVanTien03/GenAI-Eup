from __future__ import annotations

import os
from typing import List, Optional, Union

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise ImportError(
        "sentence-transformers chưa được cài. Hãy `pip install sentence-transformers`."
    ) from e


def _get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy biến môi trường theo thứ tự:
    1) os.environ
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


class CustomEmbeddings:
    def __init__(self, model_name: str, device: Optional[str] = None):
        """
        Args:
            model_name: tên model HF (vd: 'sentence-transformers/all-MiniLM-L6-v2')
            device: 'cpu' | 'cuda' | None (None để auto theo sentence-transformers)
        """
        # SentenceTransformer tự chọn device nếu None
        self.model = SentenceTransformer(model_name, device=device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not isinstance(texts, list):
            raise TypeError("texts phải là List[str]")
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        if not isinstance(text, str):
            raise TypeError("text phải là str")
        return self.model.encode(text, convert_to_numpy=True).tolist()


def create_embeddings(
    model_name: Optional[str] = None,
    *,
    device: Optional[str] = None,
) -> CustomEmbeddings:
    """
    Tạo CustomEmbeddings dùng sentence-transformers.

    Ưu tiên lấy tên model theo thứ tự:
      1) Tham số `model_name`
      2) ENV EMBEDDING_MODEL_NAME (os hoặc .env nếu có)
      3) Mặc định: 'sentence-transformers/all-MiniLM-L6-v2'
    """
    try:
        name = (
            model_name
            or _get_env_var("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        )
        return CustomEmbeddings(model_name=name, device=device)
    except Exception as e:
        # Không sys.exit(); để caller xử lý
        raise RuntimeError(f"Error creating embeddings: {e}") from e
