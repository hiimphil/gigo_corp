# ai_script_module.py
import openai
import os
from dotenv import load_dotenv
import re
import prompt_config

# --- Removed feedback_module and world_data_manager imports ---

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
        except ImportError: pass
        except Exception: pass
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

# --- Removed format_examples_for_prompt function ---
# --- Removed generate_observations function ---

# --- Refactored: Simplified function signature and logic ---
def generate_ai_script(optional_theme="",
                       temperature=0.7,
                       max_tokens=200,
                       num_script_options=1):
    """
    Generates one or more 4-line conversational comic scripts using the narrative prompt.
    """
    client, error_msg = load_api_key_and_init_client()
    if error_msg: return error_msg

    # --- Removed feedback and world context logic ---

    # --- Refactored: Handle empty/whitespace-only theme ---
    final_theme = optional_theme if optional_theme and optional_theme.strip() else "general office life or modern absurdities"

    # --- Refactored: Simplified prompt formatting ---
    user_prompt = prompt_config.SCRIPT_USER_PROMPT_TEMPLATE.format(
        char_a_full_desc=prompt_config.CHARACTER_A_BASE_PERSONALITY,
        char_b_full_desc=prompt_config.CHARACTER_B_BASE_PERSONALITY,
        char_c_full_desc=prompt_config.CHARACTER_C_BASE_PERSONALITY,
        optional_theme=final_theme
    )

    raw_response_for_debugging = None
    try:
        print(f"Attempting to generate {num_script_options} AI script(s). Theme: '{final_theme}'")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_config.SCRIPT_SYSTEM_MESSAGE},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens * num_script_options,
            n=num_script_options,
            stop=None
        )
        raw_response_for_debugging = response

        generated_scripts = []
        if response.choices and len(response.choices) > 0:
            for choice in response.choices:
                if choice.message and choice.message.content:
                    script_content = choice.message.content.strip()
                    lines = [line.strip() for line in script_content.split('\n') if line.strip()]
                    final_lines_for_choice = []
                    for line_val in lines:
                        if line_val.upper().startswith("A:") or \
                           line_val.upper().startswith("B:") or \
                           line_val.upper().startswith("C:"):
                            final_lines_for_choice.append(line_val)
                    
                    if len(final_lines_for_choice) == 4:
                        generated_scripts.append("\n".join(final_lines_for_choice))
                    else:
                        print(f"Warning: A generated script choice did not result in 4 valid A/B/C: lines. Original: {script_content}")
            
            if generated_scripts:
                return generated_scripts if num_script_options > 1 else generated_scripts[0]
            else:
                all_choices_content = [ch.message.content for ch in response.choices if ch.message]
                return f"Error: AI generated choices, but none resulted in a valid 4-line script. Raw choices content:\n{all_choices_content}"
        else:
            return "Error: AI response (script gen) did not contain any choices."

    except openai.APIError as e:
        print(f"OpenAI API Error (Script Gen): {e}")
        if raw_response_for_debugging: print(f"Raw OpenAI Response (Script Gen APIError): {raw_response_for_debugging}")
        return f"Error: OpenAI API error during script generation: {e}"
    except Exception as e:
        print(f"Unexpected error (Script Gen): {type(e).__name__} - {e}")
        if raw_response_for_debugging: print(f"Raw OpenAI Response (Script Gen Exception): {raw_response_for_debugging}")
        return f"Error: Unexpected error during script generation: {e}"

# --- Platform Caption Generation Functions ---
def _generate_single_caption(client, comic_script, platform_prompt_template, platform_name, temperature=0.6, max_tokens=100):
    user_caption_prompt = platform_prompt_template.format(comic_script=comic_script)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": prompt_config.CAPTION_SYSTEM_MESSAGE},
                {"role": "user", "content": user_caption_prompt}
            ],
            temperature=temperature, max_tokens=max_tokens, n=1
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            caption = response.choices[0].message.content.strip()
            if caption.startswith('"') and caption.endswith('"'): caption = caption[1:-1]
            return caption
        else:
            return f"Error: No content from {platform_name} caption generation."
    except Exception as e:
        print(f"Error generating {platform_name} caption: {type(e).__name__} - {e}")
        return f"Error: Could not generate {platform_name} caption ({type(e).__name__})."

def generate_platform_captions(comic_script):
    client, error_msg = load_api_key_and_init_client()
    if error_msg:
        return {"instagram": error_msg, "bluesky": error_msg, "twitter": error_msg, "error": True}
    captions = {}
    platforms = {
        "instagram": prompt_config.INSTAGRAM_CAPTION_PROMPT_TEMPLATE,
        "bluesky": prompt_config.BLUESKY_CAPTION_PROMPT_TEMPLATE,
        "twitter": prompt_config.TWITTER_CAPTION_PROMPT_TEMPLATE
    }
    for platform, template in platforms.items():
        captions[platform] = _generate_single_caption(client, comic_script, template, platform.capitalize())
    captions["error"] = any(str(caption).startswith("Error:") for caption in captions.values())
    return captions

if __name__ == '__main__':
    print("Testing ai_script_module.py with Character C, optional world data, and multi-script options...")
    try:
        feedback_module.init_db() 
        world_data_manager.load_all_world_data() 
    except Exception as e:
        print(f"Error during init for testing: {e}")

    test_theme_input = "a new mandatory 'synergy' workshop"
    test_char_a_mood_input = "suspiciously cheerful"
    test_char_b_mood_input = "already over it"
    test_char_c_mood_input = "trying to lead the 'downward-facing data-dog' pose"

    print(f"\n--- Generating Script WITH World Context ---")
    generated_script_with_context = generate_ai_script(
        optional_theme=test_theme_input,
        char_a_mood=test_char_a_mood_input,
        char_b_mood=test_char_b_mood_input,
        char_c_mood=test_char_c_mood_input,
        use_world_context=True, 
        temperature=0.7,
        num_good_examples=1,
        num_script_options=2 # Test with 2 options
    )
    print("\n--- Generated Script(s) (With World Context) ---")
    if isinstance(generated_script_with_context, list):
        for i, script in enumerate(generated_script_with_context):
            print(f"Option {i+1}:\n{script}\n---")
    else:
        print(generated_script_with_context)
    print("------------------------")

    print(f"\n--- Generating Script WITHOUT World Context ---")
    generated_script_no_context = generate_ai_script(
        optional_theme=test_theme_input,
        char_a_mood=test_char_a_mood_input,
        char_b_mood=test_char_b_mood_input,
        char_c_mood=test_char_c_mood_input,
        use_world_context=False, 
        temperature=0.7,
        num_good_examples=1,
        num_script_options=1 # Test with 1 option
    )
    print("\n--- Generated Script (No World Context) ---")
    print(generated_script_no_context)
    print("------------------------")

    # Test caption generation if a script was successful
    script_to_caption = None
    if isinstance(generated_script_with_context, list) and generated_script_with_context and not generated_script_with_context[0].startswith("Error:"):
        script_to_caption = generated_script_with_context[0]
    elif isinstance(generated_script_with_context, str) and not generated_script_with_context.startswith("Error:"):
        script_to_caption = generated_script_with_context
    
    if script_to_caption:
        print(f"\n--- Generating Platform Captions for script: ---\n{script_to_caption}\n-------------------------------------------")
        generated_captions = generate_platform_captions(script_to_caption)
        if not generated_captions.get("error"):
            print(f"\nInstagram Caption Suggestion:\n{generated_captions['instagram']}")
            print(f"\nBluesky Caption Suggestion:\n{generated_captions['bluesky']}")
            print(f"\nTwitter Caption Suggestion:\n{generated_captions['twitter']}")
        else:
            print("\nError generating one or more captions:")
            if str(generated_captions.get("instagram","")).startswith("Error:"): print(f"Instagram: {generated_captions['instagram']}")
            if str(generated_captions.get("bluesky","")).startswith("Error:"): print(f"Bluesky: {generated_captions['bluesky']}")
            if str(generated_captions.get("twitter","")).startswith("Error:"): print(f"Twitter: {generated_captions['twitter']}")
        print("-------------------------------------------")
    else:
        print("Skipping caption generation test due to script generation failure or error.")
