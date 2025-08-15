import sys
import os
import requests
from dotenv import load_dotenv
from typing import Optional, List, Any
from pydantic import Field

from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import LLMChain
from langchain_community.llms import LlamaCpp
from langchain_community.llms.google_palm import GooglePalm
from langchain_groq import ChatGroq
from langchain.llms.base import LLM

# Load environment variables from .env file
load_dotenv()

def initialize_llm(llm_type: str = "gemini", model_path: str = None) -> Any:
    try:
        # Use default model path from env if not provided
        model_path = model_path or os.getenv("LLM_MODEL_PATH")

        if llm_type == "local":
            if not model_path:
                raise ValueError("LLM_MODEL_PATH must be set for local LLMs (LlamaCpp)")

            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            return LlamaCpp(
                model_path=model_path,
                n_ctx=2048,
                verbose=False,
                callback_manager=callback_manager,
                n_gpu_layers=1,
            )

        elif llm_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI LLM")

            return ChatGroq(
                temperature=0,
                groq_api_key=api_key,
                model_name="llama-3.3-70b-versatile"
            )

        elif llm_type == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY must be set for Google LLM")

            return GooglePalm(google_api_key=api_key)

        elif llm_type == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
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
                        "contents": [
                            {
                                "parts": [{"text": prompt}]
                            }
                        ]
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

            return GeminiLLM(api_key=api_key)

        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    except Exception as e:
        print(f"Error initializing LLM: {e}")
        sys.exit(1)
