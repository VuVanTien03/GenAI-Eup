# LangChain Agents & Memory
from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from typing import List, Union, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_community.utilities import WikipediaAPIWrapper
from src.utils.vector_store import get_similar_docs
import sys


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
