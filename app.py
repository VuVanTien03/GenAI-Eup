from fastapi import FastAPI
from pydantic import BaseModel
from main import load_document, initialize_llm, create_embeddings, create_agent, load_vector_store, create_vector_store, create_learning_path
import os
import sys
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware
from langchain.memory import ConversationBufferMemory
import json

config = dotenv_values(".env")

app = FastAPI()

# Cho phép tất cả origin (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🛡 Có thể thay bằng ["http://localhost:3000"] cho frontend cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Body(BaseModel):
    query: str
    level: str | None = None

@app.get("/")
def root():
    return {"Hello": "World"}


@app.post("/query")
def create(req: Body ):
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
            vector_store = load_vector_store(db_path=config['VECTORDB_PATH'], embeddings=embeddings)
        else:
            vector_store = create_vector_store(documents, embeddings)
        # vector_store.persist()  # Make sure to persist

        # 3. Initialize LLM
        llm = initialize_llm() # Or "openai" or "google"
        # 4. Initialize Agent
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # 5. Get user input and create learning path
        learning_goal = req.query
        user_knowledge = req.level
        learning_path = create_learning_path(agent, learning_goal, user_knowledge)


    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        print("Exiting program.")
    return json.loads(learning_path)