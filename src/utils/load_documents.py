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


def crawler_roadmap_to_docs(roadmap_data: Union[Dict, List[Dict]]) -> List[Document]:
    """
    Convert roadmap data from crawler (roadmap.sh) into LangChain Documents.

    Expected crawler schema (single item):
    {
      "title": "AI Engineer Roadmap",
      "skills": [
        {"name": "Python", "subskills": ["Syntax", "OOP", "Data Structures"]},
        {"name": "Machine Learning", "subskills": ["Supervised", "Unsupervised"]}
      ],
      "learning_path": []  # optional/empty
    }

    Can also accept a list of such objects.
    """
    items: List[Dict] = []
    if isinstance(roadmap_data, dict):
        items = [roadmap_data]
    elif isinstance(roadmap_data, list):
        items = roadmap_data
    else:
        raise ValueError("roadmap_data must be dict or list of dicts.")

    docs: List[Document] = []
    for item in items:
        title = item.get("title", "")
        skills = item.get("skills", []) or []
        lp = item.get("learning_path", []) or []

        blocks: List[str] = []
        for sk in skills:
            sk_name = (sk or {}).get("name", "")
            subskills = (sk or {}).get("subskills", []) or []
            # subskills từ crawler là list[str]
            block = [f"Skill: {sk_name}"]
            for ss in subskills:
                block.append(f"  - {str(ss)}")
            blocks.append("\n".join(block))

        # Nếu có learning_path (dù đang rỗng theo code crawler), vẫn serialize an toàn
        lp_text = ""
        if isinstance(lp, list) and lp:
            lp_lines = ["Learning Path:"]
            for step in lp:
                if isinstance(step, dict):
                    w = step.get("week") or step.get("step") or "N/A"
                    obj = step.get("objective") or step.get("title") or ""
                    lp_lines.append(f"  Week/Step {w}: {obj}")
                else:
                    lp_lines.append(f"  - {str(step)}")
            lp_text = "\n" + "\n".join(lp_lines)

        page = f"Target: {title}\n" + "\n\n".join(blocks) + lp_text
        docs.append(Document(page_content=page, metadata={"title": title, "source": "roadmap.sh"}))

    return docs