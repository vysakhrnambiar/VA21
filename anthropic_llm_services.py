# anthropic_llm_services.py
import os
import anthropic
import json
from datetime import datetime
import logging
import requests
from typing import Callable, Optional

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

def get_claude_html_response_with_thinking_stream(
    user_prompt: str,
    system_instruction: str,
    model_name: str = "claude-3-5-sonnet-20241022",
    max_tokens_to_sample: int = 8000,
    thinking_callback_url: Optional[str] = None
) -> str:
    """
    Generates HTML using Anthropic Claude API with streaming thinking tokens.
    
    Args:
        user_prompt: The user's query.
        system_instruction: System instructions for Claude.
        model_name: The Claude model to use.
        max_tokens_to_sample: Max output tokens.
        thinking_callback_url: URL to POST thinking tokens to (e.g., http://localhost:8001/api/thinking_stream)
    
    Returns:
        The generated HTML string or an error message.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment.")
        return "Error: Anthropic API key not configured."

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Send thinking_start event
        if thinking_callback_url:
            try:
                logger.info(f"Sending thinking_start to {thinking_callback_url}")
                response = requests.post(thinking_callback_url, json={
                    "type": "thinking_start",
                    "payload": {"message": "Starting to think about your request..."}
                }, timeout=1)
                logger.info(f"thinking_start response: {response.status_code}")
            except Exception as e:
                logger.warning(f"Failed to send thinking_start: {e}")

        # Create streaming request with thinking enabled
        stream = client.messages.create(
            model=model_name,
            max_tokens=max_tokens_to_sample,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000  # Must be less than max_tokens (8000)
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
            system=system_instruction,
            stream=True  # Enable streaming
        )

        thinking_content = ""
        response_content = ""
        
        # Process streaming response
        for event in stream:
            if event.type == "content_block_start":
                block = event.content_block
                if hasattr(block, 'type') and block.type == "thinking":
                    # Thinking block started
                    logger.debug("Thinking block started")
                    
            elif event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, 'type'):
                    if delta.type == "thinking_delta":
                        # Thinking content delta - FIXED: Use delta.thinking not delta.text!
                        thinking_text = getattr(delta, 'thinking', '')
                        thinking_content += thinking_text
                        
                        # Send thinking delta to frontend
                        if thinking_callback_url and thinking_text:
                            try:
                                logger.info(f"Sending thinking_delta: {len(thinking_text)} chars")
                                response = requests.post(thinking_callback_url, json={
                                    "type": "thinking_delta",
                                    "payload": {"content": thinking_text}
                                }, timeout=1)
                                logger.info(f"thinking_delta response: {response.status_code}")
                            except Exception as e:
                                logger.warning(f"Failed to send thinking_delta: {e}")
                    
                    elif delta.type == "text_delta":
                        # Regular response content delta
                        response_text = getattr(delta, 'text', '')
                        response_content += response_text
                        
            elif event.type == "content_block_stop":
                # Block ended
                logger.debug("Content block stopped")
                
            elif event.type == "message_stop":
                # Message completed
                logger.debug("Message completed")
                break

        # Send thinking_end event
        if thinking_callback_url:
            try:
                requests.post(thinking_callback_url, json={
                    "type": "thinking_end",
                    "payload": {"message": "Thinking complete, generating final response..."}
                }, timeout=1)
            except Exception as e:
                logger.warning(f"Failed to send thinking_end: {e}")

        logger.info(f"Claude streaming response (first 200 chars): {response_content[:200]}")
        logger.info(f"Claude thinking tokens captured: {len(thinking_content)} characters")
        
        return response_content.strip() if response_content else "Error: No response content received"
        
    except anthropic.APIConnectionError as e:
        logger.error(f"Claude API connection error: {e}")
        # Send error to frontend
        if thinking_callback_url:
            try:
                requests.post(thinking_callback_url, json={
                    "type": "thinking_error",
                    "payload": {"error": f"Connection error: {str(e)}"}
                }, timeout=1)
            except:
                pass
        return f"Error: Claude API connection error: {e}"
        
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API status error: {e}")
        # Send error to frontend
        if thinking_callback_url:
            try:
                requests.post(thinking_callback_url, json={
                    "type": "thinking_error",
                    "payload": {"error": f"API error: {str(e)}"}
                }, timeout=1)
            except:
                pass
        return f"Error: Claude API status error - Code: {e.status_code}, Message: {e.message}"
    
    except Exception as e:
        logger.exception(f"Unexpected error during Claude streaming API call: {e}")
        # Send error to frontend
        if thinking_callback_url:
            try:
                requests.post(thinking_callback_url, json={
                    "type": "thinking_error",
                    "payload": {"error": f"Unexpected error: {str(e)}"}
                }, timeout=1)
            except:
                pass
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