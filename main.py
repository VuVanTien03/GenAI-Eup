import os
import sys
from typing import List, Union, Dict, Any
from dotenv import dotenv_values
from langchain_groq import ChatGroq
# LangChain Core
from langchain.chains import LLMChain

from langchain_core.prompts import PromptTemplate
# from langchain_community.llms import GooglePalm
# LangChain Community
from langchain_community.llms.google_palm import GooglePalm

from langchain_community.llms import LlamaCpp
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader, YoutubeLoader
from langchain_community.utilities import WikipediaAPIWrapper

# LangChain Agents & Memory
from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory

# Callbacks
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Text splitting
from langchain.text_splitter import RecursiveCharacterTextSplitter


config = dotenv_values(".env")

def load_document(file_path: str) -> Union[List[str], str]:
    """
    Loads a document from a file or URL and returns the text content.
    Handles text, PDF, web pages, and YouTube videos.

    Args:
        file_path: Path to the document or URL.

    Returns:
        A list of documents.
    """
    try:
        if file_path.startswith("http://") or file_path.startswith("https://"):
            if "youtube.com" in file_path:
                loader = YoutubeLoader.from_url(file_path)  # Use YoutubeLoader
            else:
                loader = WebBaseLoader(file_path)
        elif file_path.lower().endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
        data = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(config['CHUNK_SIZE']), chunk_overlap=int(config['CHUNK_OVERLAP'])
        )
        chunks = text_splitter.split_documents(data)
        return chunks
    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
        return []  # Return an empty list on error to prevent crashing

from sentence_transformers import SentenceTransformer

class CustomEmbeddings:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text):
        return self.model.encode(text, convert_to_numpy=True).tolist()

def create_embeddings(model_name: str = config["EMBEDDING_MODEL_NAME"]) -> CustomEmbeddings:
    """
    Creates and returns a CustomEmbeddings object using sentence-transformers directly.

    Args:
        model_name: Name of the HuggingFace model to use.

    Returns:
        An embedding object with embed_documents and embed_query methods.
    """
    try:
        embeddings = CustomEmbeddings(model_name=model_name)
        return embeddings
    except Exception as e:
        print(f"Error creating embeddings: {e}")
        sys.exit(1)


def create_vector_store(
    texts: List[str], embeddings: HuggingFaceEmbeddings, db_path: str = config['VECTORDB_PATH']
) -> Chroma:
    """
    Creates and persists a Chroma vector store from a list of texts and embeddings.

    Args:
        texts: List of text strings to store.
        embeddings: The embedding model.
        db_path: Path to store the Chroma database.

    Returns:
        A Chroma object.
    """
    try:
        vector_store = Chroma.from_documents(texts, embeddings, persist_directory=db_path)
        return vector_store
    except Exception as e:
        print(f"Error creating vector store: {e}")
        sys.exit(1)  # Exit if vector store creation fails


def load_vector_store(
    db_path: str = config['VECTORDB_PATH'], embeddings: HuggingFaceEmbeddings = None
) -> Chroma:
    """Loads an existing Chroma vector store. If embeddings is None, it uses
    the default embedding model.
    """
    try:
        if embeddings is None:
            embeddings = create_embeddings()
        vector_store = Chroma(
            persist_directory=db_path, embedding_function=embeddings
        )  # Use embedding_function
        return vector_store
    except Exception as e:
        print(f"Error loading vector store: {e}")
        sys.exit(1)  # Exit if loading fails


def get_similar_docs(query: str, vector_store: Chroma, k: int = 5) -> List[str]:
    """
    Retrieves the most similar documents from the vector store for a given query.

    Args:
        query: The query string.
        vector_store: The Chroma vector store.
        k: The number of similar documents to retrieve.

    Returns:
        A list of the most similar documents.
    """
    try:
        return vector_store.similarity_search(query, k=k)
    except Exception as e:
        print(f"Error retrieving similar documents: {e}")
        return []  # Return empty list


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


def create_agent(llm: Any, vector_store: Chroma, memory: ConversationBufferMemory) -> Any:
    """
    Creates an agent that can answer questions about the documents in the vector store
    and carry on a conversation.

    Args:
        llm: The language model.
        vector_store: The vector store containing the document embeddings.
        memory: Conversation buffer.

    Returns:
        An agent.
    """
    try:
        # Khởi tạo Wikipedia wrapper
        wiki = WikipediaAPIWrapper()

        # Định nghĩa các tool
        tools = [
            Tool.from_function(
                func=lambda q: get_similar_docs(q, vector_store),
                name="learning_material_qa",
                description="Useful for answering questions about the learning materials."
            ),
            Tool.from_function(
                func=wiki.run,
                name="Wikipedia",
                description="Useful for answering general knowledge questions using Wikipedia."
            ),
        ]

        # Khởi tạo agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=memory,
            verbose=True,
        )
        return agent
    except Exception as e:
        print(f"Error creating agent: {e}")
        sys.exit(1)

def create_learning_path(agent: Any, learning_goal: str, user_knowledge: str = "") -> str:
    """
    Creates a personalized learning path using the agent.

    Args:
        agent: The initialized agent.
        learning_goal: The user's learning goal.
        user_knowledge: The user's current knowledge (optional).

    Returns:
        A JSON string with "skills" and "learning_path".
    """
    try:
        prompt = f"""
        You are a helpful AI assistant designed to create personalized learning paths.
        The user's learning goal is: "{learning_goal}".
        """
        if user_knowledge:
            prompt += f'The user has some existing knowledge: "{user_knowledge}".'
        prompt += """
        Return your result in JSON format with the following structure:

        {
          "skills": [list of skills the user needs to learn],
          "learning_path": [
            {
              "day": 1,
              "objective": "...",
              "resources": ["resource1", "resource2"],
              "theory": "...",
              "question review": ""
            },
            ...
          ]
        }
                                                                                                                                                           
        - "skills" is a list of required skills.
        - Each "learning_path" day should have a number, clear objective, suggested resources (text/video/interactive), and a way to assess understanding (quiz, project, etc).
        Do not include explanation outside the JSON.
        - Each question review of a day is choice question A,B,C,D and have answer for each question
        """
        return agent.run(prompt.strip())
    except Exception as e:
        print(f"Error creating learning path: {e}")
        return "Sorry, I could not create a learning path."


def main():
    """
    Main function to orchestrate the learning path generation.
    """
    try:
        # 1. Load and process documents
        document_paths = [
            "data/example1.txt",
        ]
        documents = []
        for doc_path in document_paths:
            docs = load_document(doc_path)
            if docs:  # Only extend if docs is not empty
                documents.extend(docs)
                print(f"Loaded document: {doc_path}")

        if not documents:
            print("No documents loaded. Exiting.")
            sys.exit(1)

        # 2. Create embeddings and vector store
        embeddings = create_embeddings()
        if os.path.exists(config['VECTORDB_PATH']):
            print("Loading existing vector store...")
            vector_store = load_vector_store(db_path=config['VECTORDB_PATH'], embeddings=embeddings)
        else:
            print("Creating new vector store...")
            vector_store = create_vector_store(documents, embeddings)
        # vector_store.persist()  # Make sure to persist

        # 3. Initialize LLM
        llm = initialize_llm() # Or "openai" or "google"
        # 4. Initialize Agent
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # 5. Get user input and create learning path
        learning_goal = input("What is your learning goal? ")
        user_knowledge = input("What is your current knowledge of this topic? (optional) ")
        learning_path = create_learning_path(agent, learning_goal, user_knowledge)
        print("\nHere is your personalized learning path:\n")
        print(learning_path)

        # 6. (Optional) Interactive conversation with the agent
        while True:
            query = input(
                "Ask me a question about the learning material (or type 'exit'): "
            )
            if query.lower() == "exit":
                break
            try:
                response = agent.run(query)
                print(response)
            except Exception as e:
                print(f"Error: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        print("Exiting program.")



if __name__ == "__main__":
    # Create dummy data files if they don't exist
    if not os.path.exists("data"):
        os.makedirs("data")
    with open("data/example1.txt", "w") as f:
        f.write(
            "This is an example document about the basics of Python programming.  It covers variables, loops, and functions."
        )
    with open("data/example2.pdf", "w") as f:
        f.write(
            "This is a dummy PDF file.  It should contain information about data structures."
        )  # A real PDF is needed for PyPDFLoader

    main()
