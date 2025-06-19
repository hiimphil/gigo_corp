# ai_script_module.py
import openai
import os
from dotenv import load_dotenv
import re
import prompt_config

def load_api_key_and_init_client():
    """Loads the OpenAI API key and initializes the OpenAI client."""
    from dotenv import find_dotenv
    dotenv_path = find_dotenv(raise_error_if_not_found=False, usecwd=True)
    if dotenv_path: load_dotenv(dotenv_path=dotenv_path, override=True)
    else:
        cwd_dotenv_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(cwd_dotenv_path): load_dotenv(dotenv_path=cwd_dotenv_path, override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except (ImportError, Exception):
            pass
    if not api_key:
        error_msg = "Error: OPENAI_API_KEY not found."
        print(error_msg)
        return None, error_msg
    try:
        client = openai.OpenAI(api_key=api_key)
        return client, None
    except Exception as e:
        error_msg = f"Error: Failed to initialize OpenAI client: {e}"
        print(error_msg)
        return None, error_msg


def generate_ai_script(partial_script="", optional_theme="any modern office theme or a general absurd situation"):
    """
    Generates or completes a 4-line comic script.
    - If partial_script is empty, generates a full 4-line script.
    - If partial_script has content, completes it to 4 lines.
    """
    client, error_msg = load_api_key_and_init_client()
    if error_msg: return error_msg

    # Shared character descriptions
    char_a_desc = prompt_config.CHARACTER_A_BASE_PERSONALITY
    char_b_desc = prompt_config.CHARACTER_B_BASE_PERSONALITY
    char_c_desc = prompt_config.CHARACTER_C_BASE_PERSONALITY
    char_d_desc = prompt_config.CHARACTER_D_BASE_PERSONALITY
    
    # Logic to decide which prompt to use
    if not partial_script.strip():
        # --- GENERATE NEW SCRIPT ---
        print("No partial script detected. Generating a new 4-line script.")
        user_prompt = prompt_config.SCRIPT_USER_PROMPT_TEMPLATE.format(
            char_a_full_desc=char_a_desc,
            char_b_full_desc=char_b_desc,
            char_c_full_desc=char_c_desc,
            char_d_full_desc=char_d_desc,
            optional_theme=optional_theme
        )
        max_tokens = 200
        is_completion = False
    else:
        # --- COMPLETE PARTIAL SCRIPT ---
        print(f"Partial script detected. Attempting to complete.")
        lines_provided = len(partial_script.strip().split('\n'))
        if lines_provided >= 4:
            return "Error: The provided script already has 4 or more lines."
        
        lines_to_generate = 4 - lines_provided
        
        user_prompt = prompt_config.SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE.format(
            lines_to_generate=lines_to_generate,
            partial_script=partial_script,
            char_a_full_desc=char_a_desc,
            char_b_full_desc=char_b_desc,
            char_c_full_desc=char_c_desc,
            char_d_full_desc=char_d_desc
        )
        max_tokens = 50 * lines_to_generate
        is_completion = True

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_config.SCRIPT_SYSTEM_MESSAGE},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.75,
            max_tokens=max_tokens,
            n=1,
            stop=None
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            generated_text = response.choices[0].message.content.strip()
            
            # Combine partial script with generated text if it was a completion
            if is_completion:
                final_script = f"{partial_script.strip()}\n{generated_text}"
            else:
                final_script = generated_text
            
            # Clean up and validate the final script
            lines = [line.strip() for line in final_script.split('\n') if line.strip() and ':' in line]
            if len(lines) == 4:
                return "\n".join(lines)
            else:
                return f"Error: AI generated a script with {len(lines)} lines instead of 4. Raw output:\n{generated_text}"
        else:
            return "Error: AI response did not contain any valid content."

    except Exception as e:
        print(f"Unexpected error during AI script generation: {e}")
        return f"Error: An unexpected error occurred: {e}"

