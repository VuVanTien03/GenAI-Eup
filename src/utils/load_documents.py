from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader, YoutubeLoader
from typing import List, Union, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import dotenv_values
import json
from langchain.schema import Document

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

def load_roadmap_json(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        documents = []
        for entry in json_data:
            target = entry.get("target", "")
            category = entry.get("category", "")
            skill_blocks = []

            for skill in entry.get("skills", []):
                skill_text = f"Skill: {skill['name']}\n"
                for sub in skill.get("subskills", []):
                    sub_text = f"  Subskill: {sub['name']}\n"
                    sub_text += "\n".join([f"    - {s}" for s in sub.get("subsubskills", [])])
                    skill_text += sub_text + "\n"
                skill_blocks.append(skill_text)

            full_text = f"Target: {target}\nCategory: {category}\n" + "\n".join(skill_blocks)
            documents.append(Document(page_content=full_text))

        return documents
    except Exception as e:
        print(f"Error loading roadmap JSON: {e}")
        return []