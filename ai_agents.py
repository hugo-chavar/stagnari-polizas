import json
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts
from chat_history_db import save_message, get_client_history

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")

client = OpenAI(api_key=API_KEY, base_url=API_URL)

logger = logging.getLogger(__name__)

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines)


def generate_query(question):
    
    prompt = prompts.get_query_prompt()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "user", "content": question}
        ],
        max_tokens=200
    )
    model_response = response.choices[0].message.content
    logger.info(f"Question:\n{question}")
    logger.info(f"Query:\n{model_response}")
    return json.loads(clean_llm_json(model_response))


def generate_response(question, csv, client_number):
    # Save the new question to the database
    save_message(client_number, "user", question)
    
    # Get the conversation history from the last 2 days
    history = get_client_history(client_number, days_limit=2)
    
    # Prepare the messages for the API call
    prompt = prompts.get_response_prompt(csv)
    messages = [{"role": "system", "content": prompt}]
    
    # Add all previous messages to the context
    for role, content in history[:-1]:  # exclude the current question which is already in history
        messages.append({"role": role, "content": content})
    
    # Add the current question (in case it wasn't saved yet)
    messages.append({"role": "user", "content": question})
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=False
    )

    model_response = response.choices[0].message.content
    logger.info(f"Final response:\n{model_response}")
    
    # Save the assistant's response to the database
    save_message(client_number, "assistant", model_response)
    
    return model_response
