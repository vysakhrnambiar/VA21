# anthropic_llm_services.py
import os
import anthropic
import json
from datetime import datetime
import logging

# --- Logging Setup ---
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s.%(funcName)s] - %(message)s')

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def get_claude_html_response(user_prompt: str, system_instruction: str, model_name: str = "claude-3-opus-20240229", max_tokens_to_sample: int = 1024) -> str:
    """
    Generates HTML using Anthropic Claude API.

    Args:
        user_prompt: The user's query.
        system_instruction: System instructions for Claude.
        model_name: The Claude model to use.
        max_tokens_to_sample: Max output tokens.

    Returns:
        The generated HTML string or an error message.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment.")
        return "Error: Anthropic API key not configured."

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model=model_name,
            max_tokens=max_tokens_to_sample,
            thinking={
            "type": "enabled",
            "budget_tokens": 5000  # Start with minimum budget
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            system=system_instruction
        )
        response_text = message.content[0].text
        # Extract the first text block of the text, but there is the possibility of the model returning multiple types
        #if isinstance(message.content[0], anthropic.types.MessageContentBlockText):
        #     response_text = message.content[0].text
        #else:
        #    response_text = "An unexpected result has returned from Claude."

        logger.info(f"Claude response (first 200 chars): {response_text[:200]}")
        return response_text.strip()
    except anthropic.APIConnectionError as e:
         logger.error(f"Claude API connection error: {e}")
         return f"Error: Claude API connection error: {e}"
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API status error: {e}")
        return f"Error: Claude API status error - Code: {e.status_code}, Message: {e.message}"

    except Exception as e:
        logger.exception(f"Unexpected error during Claude API call: {e}")
        return f"Error: An unexpected error occurred with the Claude API: {e}"
if __name__ == '__main__':
    # Example Usage (requires ANTHROPIC_API_KEY in .env)
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("Please set your ANTHROPIC_API_KEY in a .env file to run this test.")
    else:
        test_prompt = "Write a haiku about data visualization."
        system_instruction = "You are a helpful AI assistant."
        print(f"\n--- Claude Test: Prompt: '{test_prompt}' ---")
        result = get_claude_html_response(user_prompt=test_prompt, system_instruction=system_instruction)
        print(f"Claude Result:\n{result}")