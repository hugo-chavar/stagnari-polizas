import json
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts
from chat_history_db import save_message, get_client_history, save_query, get_query_history
from policy_data import get_surnames_prompt

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")

client = OpenAI(api_key=API_KEY, base_url=API_URL)

logger = logging.getLogger(__name__)

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    # logger.info(f"Raw response from LLM:\n{raw_response}")
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    clean_llm_json = "\n".join(lines)
    # logger.info(f"Cleaned LLM JSON:\n{clean_llm_json}")
    return clean_llm_json


def generate_query(question, client_number):
    # Save the new question to the database
    save_query(client_number, "user", question)
    
    # Get the conversation history from the last 2 days
    history = get_query_history(client_number, days_limit=2)
    
    prompt = prompts.get_query_prompt()
    surnames_prompt = get_surnames_prompt()
    messages = [
        {"role": "system", "content": prompt}
    ]
    # Use the history messages, excluding the current question if already saved
    for role, content in history[:-1]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    
    # logger.info(f"Messages for query generation:\n{messages}")
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=400
    )
    model_response = response.choices[0].message.content
    logger.info(f"Question:\n{question}")
    logger.info(f"Query:\n{model_response}")
    save_query(client_number, "assistant", model_response)
    return json.loads(clean_llm_json(model_response))


def generate_response(question, csv, client_number, negative_response):
    line_count = csv.count('\n') - 1
    has_rows  = line_count > 0
    if has_rows:
        csv = csv.replace("\n", " ").replace(",", ",\n")
        # Save the new question to the database
        save_message(client_number, "user", question)
        
        # Get the conversation history from the last 2 days
        history = get_client_history(client_number, days_limit=2)
        
        # Prepare the messages for the API call
        prompt = prompts.get_response_prompt()
        messages = [{"role": "system", "content": prompt}]
        
        # Add all previous messages to the context
        for role, content in history[:-1]:  # exclude the current question which is already in history
            messages.append({"role": role, "content": content})
        
        
        messages.append({"role": "system", "content": f"CSV data: {csv}" if has_rows else "CSV data: EMPTY"})
        # Add the current question (in case it wasn't saved yet)
        messages.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=False
        )

        model_response = response.choices[0].message.content
        # Clean the response to remove any unwanted formatting
        model_response = model_response.replace("**", "*").strip()
        
        # Save the assistant's response to the database
        save_message(client_number, "assistant", model_response)
        
        return model_response
    else:
        logger.info("No data found for the query.")
        return negative_response
