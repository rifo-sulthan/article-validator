import sys
import json
import os
import logging
from dotenv import load_dotenv

# Ensure we are in the script's directory so .env is found
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def generate_config_from_ai(prompt):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in environment variables.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI library not installed. Please run: pip install openai")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    system_prompt = """
    You are a configuration generator for an article validation system.
    Your goal is to output a strictly valid JSON object based on the user's topic description.
    
    The JSON schema must be:
    {
        "candidate_labels": ["List", "of", "approx", "5-6", "relevant", "categories", "plus", "not related"],
        "positive_labels": ["Subset", "of", "candidate_labels", "that", "match", "the", "user's", "goal"],
        "step1_prefilter": {
            "force_valid_keywords": ["List", "of", "10-15", "strong", "keywords", "present", "in", "titles/urls"]
        }
    }
    
    Do not output any markdown formatting (like ```json), just the raw JSON string.
    """

    logging.info("Sending request to OpenRouter (Model: tngtech/deepseek-r1t2-chimera:free)...")
    
    completion = client.chat.completions.create(
        model="tngtech/deepseek-r1t2-chimera:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Topic: {prompt}"}
        ]
    )
    
    content = completion.choices[0].message.content.strip()
    # Clean up possible markdown code blocks if the model ignores instruction
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
        
    return json.loads(content)

def main():
    print("--- AI Config Generator ---")
    
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            prompt = input("Enter topic (e.g. 'find golf gift guides'): ")
        except (EOFError, KeyboardInterrupt):
            return

    if not prompt.strip():
        print("Empty prompt.")
        return

    print(f"\nGeneratig config for: '{prompt}'\n")
    config = generate_config_from_ai(prompt)
    
    print("\n" + json.dumps(config, indent=4))
    print("\n--------------------------------------")
    print("Copy the fields above into your config.json")

if __name__ == "__main__":
    main()
