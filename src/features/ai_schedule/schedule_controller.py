from src.utils.load_documents import load_document, crawler_roadmap_to_docs
from src.utils.vector_store import load_vector_store, create_vector_store
from dotenv import dotenv_values
from src.utils.custom_emb import create_embeddings
from src.utils.initialize_llms import initialize_llm
from src.utils.create_agent import create_agent
from src.utils.learning_path import create_learning_path
from langchain.memory import ConversationBufferMemory
import os
import json

config = dotenv_values(".env")



def GenSchedule(req, roadmap_data=None):
    try:
        # --- Load documents ---
        documents = crawler_roadmap_to_docs(roadmap_data)
        if not documents:
            return "No documents found to load."

        # --- Embeddings + Vector Store ---
        embeddings = create_embeddings()
        vectordb_path = config.get("VECTORDB_PATH")
        if vectordb_path and os.path.exists(vectordb_path):
            vector_store = load_vector_store(db_path=vectordb_path, embeddings=embeddings)
        else:
            vector_store = create_vector_store(documents, embeddings)

        # --- LLM, Agent ---
        llm = initialize_llm()
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # --- Create learning path ---
        learning_goal = req.query
        user_knowledge = req.level
        deadline = req.deadline

        learning_path = create_learning_path(agent, learning_goal, deadline, user_knowledge)

        if not learning_path:
            return "LLM returned empty learning path."

        # ✅ Trả về câu trả lời gốc thay vì ép sang JSON
        return learning_path

    except Exception as e:
        return f"Error: {str(e)}"
