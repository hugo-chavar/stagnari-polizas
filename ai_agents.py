import json
import os
from openai import OpenAI
import prompts

client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines)


def generate_query(question):
    
    prompt = prompts.get_query_prompt()
    # TODO: replace accents
    example_question = prompts.get_example_query_question()
    example_response = prompts.get_example_query_answer()
    # question2 = "Quiero obtener vehiculos que son modelo 2016 o superior y que son marca ford"
    
    response = client.chat.completions.create(
        model="gemma3",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "user", "content": example_question},
            {"role": "assistant", "content": example_response},
            {"role": "user", "content": question}
        ],
        max_tokens=200
    )
    model_response = response.choices[0].message.content
    print(f"Response:\n{model_response}")
    return json.loads(model_response)

def generate_response(question, csv):
    prompt = prompts.get_response_prompt(csv)
    example_question = prompts.get_example_question()
    example_answer = prompts.get_example_answer()
    response = client.chat.completions.create(
        model="gemma3", #"deepseek-r1:1.5b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": example_question},
            {"role": "assistant", "content": example_answer},
            {"role": "user", "content": question},
        ],
        stream=False
    )

    return response.choices[0].message.content
