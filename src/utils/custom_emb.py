from sentence_transformers import SentenceTransformer
from dotenv import dotenv_values
import sys

config = dotenv_values(".env")
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
