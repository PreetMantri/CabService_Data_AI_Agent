from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def pick_llm(Level : str):
    """
    Picks the appropriate LLM based on the provided level.

    Args:
        level (str): The level of the LLM to pick. Can be "basic", "intermediate", or "advanced".

    Returns:
        str: The name of the picked LLM.
    """
    if Level.lower() == "low":
        # Updated from 2.5-flash to 3.6-flash
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
    elif Level.lower() == "medium":
        # Updated to the standard mid-tier Pro model
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    elif Level.lower() == "high":
        # Updated to a high-tier model (e.g., Ultra or highest Pro version available)
        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0)
    else:
        raise ValueError("Invalid level provided. Please choose from 'low', 'medium', or 'high'.")
    return llm

# llm = pick_llm("high")  # Example usage, you can change the level as needed
# print(llm.invoke("What is the capital of France?"))