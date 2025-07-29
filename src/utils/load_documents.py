from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader, YoutubeLoader
from typing import List, Union, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import dotenv_values

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

