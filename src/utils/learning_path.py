from typing import List, Union, Dict, Any


def create_learning_path(agent: Any, learning_goal: str, user_knowledge: str = "") -> str:
    """
    Creates a personalized learning path using the agent.

    Args:
        agent: The initialized agent.
        learning_goal: The user's learning goal.
        user_knowledge: The user's current knowledge (optional).

    Returns:
        A JSON string with "skills" and "learning_path".
    """
    try:
        prompt = f"""
                You are a helpful AI assistant designed to create personalized learning paths.
                The user's learning goal is: "{learning_goal}".
                """
        if user_knowledge:
            prompt += f'The user has some existing knowledge: "{user_knowledge}".'
            prompt += """
                        Return your result in JSON format with the following structure:

                        {
                          "skills": [list of skills the user needs to learn],
                          "learning_path": [
                            {
                              "week": 1,
                              "objective": "...",
                            },
                            ...
                          ]
                        }
                        """

        return agent.run(prompt.strip())
    except Exception as e:
        print(f"Error creating learning path: {e}")
        return "Sorry, I could not create a learning path."
