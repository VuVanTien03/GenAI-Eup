from src.utils.load_documents import load_document, load_roadmap_json
from src.utils.vector_store import load_vector_store, create_vector_store
from dotenv import dotenv_values
from src.utils.custom_emb import create_embeddings
from src.utils.initialize_llms import initialize_llm
from src.utils.create_agent import create_agent
from src.utils.learning_path import create_learning_path
from langchain.memory import ConversationBufferMemory
import sys
import os
from src.constant import ScheduleType
import json

config = dotenv_values(".env")
def GenSchedule(req: ScheduleType):
    print(req)
    try:
        # --- Load documents ---
        document_paths = ["/home/vuvantien/PycharmProjects/GenAI-Eup/roadmap_crawler/parsed_data_raw/processed_json/AI engineer.json"]
        documents = []
        for doc_path in document_paths:
            docs = load_roadmap_json(doc_path)
            if docs:
                documents.extend(docs)
                print(f"Loaded document: {doc_path}")

        if not documents:
            print("No documents loaded.")
            return {"error": "No documents found to load."}

        # --- Embeddings + Vector Store ---
        embeddings = create_embeddings()
        if os.path.exists(config['VECTORDB_PATH']):
            vector_store = load_vector_store(db_path=config['VECTORDB_PATH'], embeddings=embeddings)
        else:
            vector_store = create_vector_store(documents, embeddings)

        # --- LLM, Agent ---
        llm = initialize_llm()
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # --- Create learning path ---
        learning_goal = req.query
        user_knowledge = req.level
        learning_path = create_learning_path(agent, learning_goal, user_knowledge)
        print(learning_path)


        if not learning_path:
            return {"error": "LLM returned empty learning path."}

        try:
            parsed = json.loads(learning_path)
            return parsed
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse learning path as JSON.",
                "raw_output": learning_path
            }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}
