import logging
import requests
from dotenv import dotenv_values
from typing import Optional, List, Any
from pydantic import Field
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp
from langchain_groq import ChatGroq
from langchain_community.llms.google_palm import GooglePalm

logger = logging.getLogger(__name__)
config = dotenv_values(".env")

def initialize_llm(llm_type: str = "gemini", model_path: Optional[str] = None) -> Any:
    try:
        if llm_type == "local":
            if not model_path:
                raise ValueError("LLM_MODEL_PATH must be set for local LLMs")
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            return LlamaCpp(
                model_path=model_path,
                n_ctx=2048,
                verbose=False,
                callback_manager=callback_manager,
                n_gpu_layers=1,
            )

        elif llm_type == "openai":
            if not config.get("GROQ_API_KEY"):
                raise ValueError("GROQ_API_KEY must be set for Groq/OpenAI API")
            return ChatGroq(
                temperature=0,
                groq_api_key=config["GROQ_API_KEY"],
                model_name="llama-3.3-70b-versatile"
            )

        elif llm_type == "google":
            if not config.get("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY must be set for Google Palm")
            return GooglePalm(google_api_key=config["GOOGLE_API_KEY"])

        elif llm_type == "gemini":
            if not config.get("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY must be set for Gemini")

            class GeminiLLM(LLM):
                api_key: str = Field(..., description="Google API key")

                def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
                    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key
                    }
                    body = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    response = requests.post(url, headers=headers, json=body)
                    if response.status_code != 200:
                        raise Exception(f"Gemini API error: {response.status_code}, {response.text}")
                    try:
                        result = response.json()
                        return result["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception as e:
                        raise Exception(f"Error parsing Gemini response: {e}")

                @property
                def _llm_type(self) -> str:
                    return "gemini"

            return GeminiLLM(api_key=config["GEMINI_API_KEY"])

        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    except Exception as e:
        logger.exception("Error initializing LLM")
        raise RuntimeError(f"Failed to initialize LLM: {e}") from e
