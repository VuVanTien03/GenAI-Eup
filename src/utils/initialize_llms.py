from __future__ import annotations

import logging
import os
from typing import Optional, List, Any

import requests
from pydantic import Field

# LangChain base
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Providers (import optional)
from langchain_community.llms import LlamaCpp
try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None  # type: ignore

try:
    # OpenAI qua LangChain (yêu cầu `langchain-openai>=0.1`)
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None  # type: ignore

try:
    # Google PaLM (đã cũ, nhưng giữ để tương thích)
    from langchain_community.llms.google_palm import GooglePalm
except Exception:
    GooglePalm = None  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------
# Helpers
# ---------------------------
def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy biến môi trường theo thứ tự ưu tiên:
    1) os.environ (Render/Railway/Heroku set ở đây)
    2) .env (nếu có `python-dotenv` và file tồn tại)
    3) default
    """
    if key in os.environ:
        return os.environ.get(key)

    try:
        from dotenv import dotenv_values  # import lười, không bắt buộc cài
        values = dotenv_values(".env")
        if key in values and values[key]:
            return values[key]
    except Exception:
        pass

    return default


# ---------------------------
# Main Factory
# ---------------------------
def initialize_llm(
    llm_type: str = "gemini",
    model_path: Optional[str] = None,
    *,
    # Common optional params
    temperature: float = 0.0,
    # LlamaCpp params
    n_ctx: int = 4096,
    n_gpu_layers: int = 1,
    n_threads: Optional[int] = None,
) -> Any:
    """
    Khởi tạo LLM linh hoạt theo `llm_type`:
      - "local"      : LlamaCpp (cần model_path)
      - "groq"       : ChatGroq (GROQ_API_KEY)
      - "openai"     : ChatOpenAI (OPENAI_API_KEY)
      - "google_palm": GooglePalm (GOOGLE_API_KEY) (cũ)
      - "gemini"     : Gọi trực tiếp REST Gemini (GEMINI_API_KEY)
    """
    try:
        if llm_type == "local":
            if not model_path:
                raise ValueError("LLM_MODEL_PATH must be set for local LLMs (model_path).")
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            return LlamaCpp(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                verbose=False,
                callback_manager=callback_manager,
            )

        elif llm_type == "groq":
            if ChatGroq is None:
                raise ImportError("langchain-groq chưa được cài hoặc không import được.")
            groq_key = get_env_var("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("GROQ_API_KEY must be set for Groq.")
            # Model phổ biến: llama-3.1-70b-versatile / llama-3.3-70b-versatile
            return ChatGroq(
                temperature=temperature,
                groq_api_key=groq_key,
                model_name=get_env_var("GROQ_MODEL", "llama-3.3-70b-versatile"),
            )

        elif llm_type == "openai":
            if ChatOpenAI is None:
                raise ImportError("langchain-openai chưa được cài hoặc không import được.")
            openai_key = get_env_var("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI.")
            # Mặc định: gpt-4o-mini (nhẹ) hoặc gpt-4.1/gpt-4o nếu có
            return ChatOpenAI(
                temperature=temperature,
                api_key=openai_key,
                model=get_env_var("OPENAI_MODEL", "gpt-4o-mini"),
            )

        elif llm_type == "google_palm":
            if GooglePalm is None:
                raise ImportError("GooglePalm không khả dụng (gói hoặc import lỗi).")
            google_key = get_env_var("GOOGLE_API_KEY")
            if not google_key:
                raise ValueError("GOOGLE_API_KEY must be set for Google Palm.")
            return GooglePalm(google_api_key=google_key, temperature=temperature)

        elif llm_type == "gemini":
            gemini_key = get_env_var("GEMINI_API_KEY")
            if not gemini_key:
                raise ValueError("GEMINI_API_KEY must be set for Gemini.")

            class GeminiLLM(LLM):
                """LLM wrapper tối giản gọi REST Gemini (Generative Language API)."""
                api_key: str = Field(..., description="Google API key")
                model: str = Field(
                    default_factory=lambda: get_env_var("GEMINI_MODEL", "gemini-2.0-flash"),
                    description="Gemini model name"
                )
                endpoint: str = Field(
                    default="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    description="Gemini endpoint template",
                )
                request_timeout: float = Field(default=30.0)

                def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
                    url = self.endpoint.format(model=self.model)
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key
                    }
                    body = {"contents": [{"parts": [{"text": prompt}]}]}
                    resp = requests.post(url, headers=headers, json=body, timeout=self.request_timeout)
                    if resp.status_code != 200:
                        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

                    try:
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception as e:
                        raise RuntimeError(f"Error parsing Gemini response: {e}")

                    # Xử lý stop tokens (LangChain bảo đảm truyền stop khi cần)
                    if stop:
                        for token in stop:
                            if token and token in text:
                                text = text.split(token)[0]
                                break
                    return text

                @property
                def _llm_type(self) -> str:
                    return "gemini-rest"

            return GeminiLLM(api_key=gemini_key)

        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    except Exception as e:
        logger.exception("Error initializing LLM")
        raise RuntimeError(f"Failed to initialize LLM: {e}") from e
