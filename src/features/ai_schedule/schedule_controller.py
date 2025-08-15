from src.utils.load_documents import load_document
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
    """
    Generate learning schedule.
    - req: ScheduleType object (có query, level)
    - roadmap_data: dữ liệu roadmap (list hoặc text) nếu có
    """
    try:
        # --- Load documents ---
        documents = []

        if roadmap_data:
            # Nếu có roadmap_data từ MongoDB, convert sang text
            if isinstance(roadmap_data, list):
                roadmap_text = "\n".join([str(item) for item in roadmap_data])
            elif isinstance(roadmap_data, dict):
                roadmap_text = json.dumps(roadmap_data, ensure_ascii=False)
            else:
                roadmap_text = str(roadmap_data)

            # Lưu tạm ra file hoặc convert trực tiếp
            temp_path = "data/temp_roadmap.txt"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(roadmap_text)

            docs = load_document(temp_path)
            if docs:
                documents.extend(docs)
                print(f"Loaded roadmap from MongoDB")
        else:
            # Nếu không có roadmap_data → fallback đọc file ví dụ
            document_paths = []
            for doc_path in document_paths:
                docs = load_document(doc_path)
                if docs:
                    documents.extend(docs)
                    print(f"Loaded document: {doc_path}")

        if not documents:
            return {"error": "No documents found to load."}

        # # --- Embeddings + Vector Store ---
        embeddings = create_embeddings()
        vectordb_path = config.get("VECTORDB_PATH")  # avoid KeyError
        if vectordb_path and os.path.exists(vectordb_path):
            vector_store = load_vector_store(
                db_path=vectordb_path,
                embeddings=embeddings
            )
        else:
            vector_store = create_vector_store(documents, embeddings)


        # --- LLM, Agent ---
        llm = initialize_llm()
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        agent = create_agent(llm, vector_store, memory)

        # --- Create learning path ---
        learning_goal = req.query
        user_knowledge = req.level
        try:
            learning_path = create_learning_path(agent, learning_goal, user_knowledge)
        except Exception as e:
            return {
                "error": "Learning path generation failed.",
                "raw_error": str(e)
            }

        if not learning_path:
            return {"error": "LLM returned empty learning path."}

        try:
            return json.loads(learning_path)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse learning path as JSON.",
                "raw_output": learning_path
            }

    except Exception as e:
        return {"error": str(e)}
