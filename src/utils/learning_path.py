from typing import Any
from datetime import datetime


def create_learning_path(agent: Any, learning_goal: str, deadline: str, user_knowledge: str = "", start_date: str = None) -> str:
    """
    Creates a personalized learning path using the agent with a deadline.

    Args:
        agent: The initialized agent.
        learning_goal: The user's learning goal.
        deadline: The final deadline to complete the learning goal (format YYYY-MM-DD).
        user_knowledge: The user's current knowledge (optional).
        start_date: Optional start date (format YYYY-MM-DD). If None, today is used.

    Returns:
        A JSON string with "skills" and "learning_path".
    """
    try:
        if start_date is None:
            start_date = datetime.today().strftime("%Y-%m-%d")

        prompt = f"""
        You are a helpful AI assistant designed to create personalized learning paths.
        The user's learning goal is: "{learning_goal}".
        The user wants to complete it by the deadline: {deadline}.
        The start date is: {start_date}.
        """

        if user_knowledge:
            prompt += f'The user has some existing knowledge: "{user_knowledge}".'

        prompt += """
        Return your result in JSON format with the following structure:

        {
          "learning_path": [
            {
              "week": 1,
              "objective": "...",
              "deadline": "YYYY-MM-DD"  // specific deadline for this week's objective
            },
            ...
          ]
        }

        - "skills" must be a list of strings.
        - "deadline" must be an actual date between start_date and the final deadline.
        - Split the total learning period into weekly objectives that fit evenly until the final deadline.
        - Do not include any explanation outside the JSON.
        """

        return agent.run(prompt.strip())
    except Exception as e:
        print(f"Error creating learning path: {e}")
        return "Sorry, I could not create a learning path."
