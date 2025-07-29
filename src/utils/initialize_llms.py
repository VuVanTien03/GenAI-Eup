import sys
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import dotenv_values
from typing import List, Union, Dict, Any
from langchain_community.llms import LlamaCpp
from langchain_groq import ChatGroq
# LangChain Core
from langchain.chains import LLMChain
from langchain_community.llms.google_palm import GooglePalm

config = dotenv_values(".env")


def initialize_llm(llm_type: str = "openai" , model_path: str = config['LLM_MODEL_PATH']) -> Any:
    try:
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
            print('aasdasasda')
            if not config.get("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY must be set for OpenAI LLM")
            from langchain_community.llms import OpenAI
            return ChatGroq( temperature=0,groq_api_key = config['OPENAI_API_KEY'], model_name = 'llama-3.3-70b-versatile')

        elif llm_type == "google":
            print("ofdsfdsagdsagwerte")
            if not config.get("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY must be set for Google LLM")

            from langchain_google_genai import GoogleGenerativeAI

            return GooglePalm(google_api_key=config["GOOGLE_API_KEY"])


        elif llm_type == "gemini":

            if not config.get("KAGGLE_API_KEY"):
                raise ValueError("KAGGLE_API_KEY must be set for Gemini")

            import requests

            from langchain.llms.base import LLM

            from pydantic import Field

            from typing import Optional, List

            class GeminiLLM(LLM):
                api_key: str = Field(..., description="Google API key")

                def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
                    url = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
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

            return GeminiLLM(api_key=config["KAGGLE_API_KEY"])

        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    except Exception as e:
        print(f"Error initializing LLM: {e}")
        sys.exit(1)
