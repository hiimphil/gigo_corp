# ai_script_module.py
import openai
import os
from dotenv import load_dotenv
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
        return None, error_msg
    try:
        client = openai.OpenAI(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Error: Failed to initialize OpenAI client: {e}"


def _generate_script(user_prompt, max_tokens, is_completion=False, partial_script=""):
    """Helper function to run the OpenAI API call."""
    client, error_msg = load_api_key_and_init_client()
    if error_msg: return error_msg

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
            return f"{partial_script.strip()}\n{generated_text}" if is_completion else generated_text
        else:
            return "Error: AI response did not contain any valid content."

    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"


def generate_comic_script(partial_script="", optional_theme="any modern office theme or a general absurd situation"):
    """Generates or completes a 4-line comic script."""
    char_descs = {
        "char_a_full_desc": prompt_config.CHARACTER_A_BASE_PERSONALITY,
        "char_b_full_desc": prompt_config.CHARACTER_B_BASE_PERSONALITY,
        "char_c_full_desc": prompt_config.CHARACTER_C_BASE_PERSONALITY,
        "char_d_full_desc": prompt_config.CHARACTER_D_BASE_PERSONALITY
    }
    
    if not partial_script.strip():
        user_prompt = prompt_config.COMIC_SCRIPT_USER_PROMPT_TEMPLATE.format(optional_theme=optional_theme, **char_descs)
        max_tokens = 200
        is_completion = False
    else:
        lines_provided = len(partial_script.strip().split('\n'))
        if lines_provided >= 4: return "Error: The provided script already has 4 or more lines."
        lines_to_generate = 4 - lines_provided
        user_prompt = prompt_config.COMIC_SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE.format(
            lines_to_generate=lines_to_generate, partial_script=partial_script, **char_descs)
        max_tokens = 50 * lines_to_generate
        is_completion = True

    return _generate_script(user_prompt, max_tokens, is_completion, partial_script)


def generate_cartoon_script(partial_script="", optional_theme="any modern office theme or a general absurd situation"):
    """Generates or completes a 4-12 line cartoon script."""
    char_descs = {
        "char_a_full_desc": prompt_config.CHARACTER_A_BASE_PERSONALITY,
        "char_b_full_desc": prompt_config.CHARACTER_B_BASE_PERSONALITY,
        "char_c_full_desc": prompt_config.CHARACTER_C_BASE_PERSONALITY,
        "char_d_full_desc": prompt_config.CHARACTER_D_BASE_PERSONALITY
    }
    
    if not partial_script.strip():
        user_prompt = prompt_config.CARTOON_SCRIPT_USER_PROMPT_TEMPLATE.format(optional_theme=optional_theme, **char_descs)
        max_tokens = 600 # More tokens for a longer script
        is_completion = False
    else:
        lines_provided = len(partial_script.strip().split('\n'))
        if lines_provided >= 12: return "Error: The provided script already has 12 or more lines."
        lines_to_generate = 12 - lines_provided
        user_prompt = prompt_config.CARTOON_SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE.format(
            lines_to_generate=lines_to_generate, partial_script=partial_script, **char_descs)
        max_tokens = 50 * lines_to_generate
        is_completion = True
        
    return _generate_script(user_prompt, max_tokens, is_completion, partial_script)
