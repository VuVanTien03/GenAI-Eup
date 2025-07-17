from typing import List, Union, Dict, Any
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import dotenv_values
from langchain_community.vectorstores import Chroma
import sys
from src.utils.custom_emb import create_embeddings

config = dotenv_values(".env")

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
