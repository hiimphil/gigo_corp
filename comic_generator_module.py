# comic_generator_module.py
import os
import re
import random
import datetime
import tempfile
from PIL import Image, ImageDraw, ImageFont
from textwrap import TextWrapper

# --- Configuration ---
IMAGE_BASE_PATH = "Images/"
FONT_PATH = "Fonts/"
TITLEFONT_PATH = os.path.join(FONT_PATH, "RNS-B.ttf")
MAIN_FONT_PATH = os.path.join(FONT_PATH, "Krungthep.ttf")

FONT_SIZE = 32
TEXT_COLOR = "#ffffff"
TEXT_POSITION = (256, 250)
SPACING_BETWEEN_LINES = 4
PANEL_WIDTH = 512
PANEL_HEIGHT = 640
OUTPUT_FILENAME_PREFIX = "gigoco_"
HEADER_TEXT = "GIGOCO"
HEADER_HEIGHT = 40
HEADER_FONT_SIZE = 40
HEADER_TEXT_COLOR = "#6d7467"
# --- End Configuration ---


def get_available_actions():
    """Scans the image directory to find all available actions, organized by character, talking state, and direction."""
    action_data = {}
    if not os.path.isdir(IMAGE_BASE_PATH):
        return action_data

    for char_folder in sorted(os.listdir(IMAGE_BASE_PATH)):
        char_path = os.path.join(IMAGE_BASE_PATH, char_folder)
        if os.path.isdir(char_path) and len(char_folder) == 1:
            action_data[char_folder] = {}
            for state_folder in os.listdir(char_path):
                state_path = os.path.join(char_path, state_folder)
                if os.path.isdir(state_path) and state_folder in ["Talking", "Nottalking"]:
                    action_data[char_folder][state_folder] = {}
                    for direction_folder in os.listdir(state_path):
                        direction_path = os.path.join(state_path, direction_folder)
                        if os.path.isdir(direction_path):
                            action_data[char_folder][state_folder][direction_folder] = []
                            for action_folder in os.listdir(direction_path):
                                if os.path.isdir(os.path.join(direction_path, action_folder)):
                                    action_data[char_folder][state_folder][direction_folder].append(action_folder)

    for char, states in action_data.items():
        for state, directions in states.items():
            for direction, actions in directions.items():
                action_data[char][state][direction] = sorted(actions)

    return action_data


def parse_script_line(line):
    """
    Parses a single line into character, action, dialogue, and direction override.
    Both actions and direction overrides are now fully case-insensitive.
    """
    match = re.match(r"^\s*([A-D]):\s*(?:\((.*?)\))?\s*(.*)", line, re.IGNORECASE)
    if not match:
        return None, "normal", None, line

    character = match.group(1).upper()
    # Convert any action text to lowercase for consistency
    action_text = (match.group(2) or "normal").lower()
    dialogue = match.group(3).strip()

    # Check for direction override
    direction_override = None
    if action_text in ["left", "right", "straight"]:
        direction_override = action_text.capitalize()  # Standardize to Left, Right, Straight
        action = "normal"  # If it's a direction, the action is normal
    else:
        action = action_text  # Otherwise, it's a regular action (now lowercase)

    return character, action, direction_override, dialogue


def determine_logical_direction(current_char, prev_char):
    """Determines the 'logical' direction the character should be looking based on conversation rules."""
    if current_char == 'C': return "Right"
    if current_char == 'B': return "Left"
    if current_char == 'A': return "Left" if prev_char == 'C' else "Right"
    if current_char == 'D': return "Straight"
    return "Straight"


def find_image_path(character, talking_state, direction, action):
    """
    Finds the best available image path with a robust fallback system.
    The folder structure is: Character / State / Direction / action (lowercase)
    Example: Images/A/Talking/Right/normal/image.jpg
    """
    directions_to_try = [direction, "Straight", "Right", "Left"]
    # The 'action' parameter is now always lowercase, as is the fallback 'normal'
    actions_to_try = [action, "normal"]
    
    unique_directions = list(dict.fromkeys(directions_to_try))
    unique_actions = list(dict.fromkeys(actions_to_try))

    paths_to_try = []
    for d in unique_directions:
        for a in unique_actions:
            # The action 'a' will now correctly match lowercase folder names (e.g., 'proud')
            paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, talking_state, d, a))

    for path in paths_to_try:
        if os.path.isdir(path):
            try:
                images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if images:
                    return os.path.join(path, random.choice(images)), None
            except Exception as e:
                print(f"--> WARNING: Could not read directory '{path}': {e}")
                continue
    
    error_msg = f"No valid image found for Char: {character}, State: {talking_state}, trying Dir: {direction}, Act: {action}"
    return None, error_msg


def process_script(script_text):
    """Processes a script and returns panel data or an error message."""
    panel_data = []
    previous_character = None
    lines = script_text.strip().split('\n')
    
    if len(lines) != 4:
        return None, "Script must have exactly 4 lines."

    for line_num, line in enumerate(lines, 1):
        character, action, direction_override, dialogue = parse_script_line(line)
        if not character:
            return None, f"Could not parse line {line_num}: '{line}'"

        final_direction = direction_override or determine_logical_direction(character, previous_character)
        talking_state = "Talking" if dialogue else "Nottalking"
        
        image_path, error = find_image_path(character, talking_state, final_direction, action)
        if error:
            return None, f"Image Error on line {line_num} ('{line}'): {error}. Check your 'Images' folder structure and file names."

        panel_data.append({"image_path": image_path, "dialogue": dialogue})
        previous_character = character
        
    return panel_data, None


def create_panel_image(image_path, dialogue, panel_num, temp_dir):
    """Creates a single panel image, returns path or error."""
    try:
        base_image = Image.open(image_path).convert("RGB")
        if base_image.size != (PANEL_WIDTH, PANEL_HEIGHT):
            base_image = base_image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    except Exception as e:
        return None, f"Could not open or resize image '{image_path}': {e}"

    draw = ImageDraw.Draw(base_image)
    if dialogue:
        try:
            font = ImageFont.truetype(MAIN_FONT_PATH, FONT_SIZE)
        except IOError:
            font = ImageFont.load_default()
        
        wrapper = TextWrapper(width=26)
        lines = wrapper.wrap(text=dialogue)
        
        ascent, descent = font.getmetrics()
        line_height = ascent + descent
        total_text_block_height = (len(lines) * line_height) + (max(0, len(lines) - 1) * SPACING_BETWEEN_LINES)
        y_text = TEXT_POSITION[1] - total_text_block_height

        for line in lines:
            line_bbox = font.getbbox(line)
            x_text = (PANEL_WIDTH - (line_bbox[2] - line_bbox[0])) / 2
            draw.text((x_text, y_text), line, font=font, fill=TEXT_COLOR)
            y_text += line_height + SPACING_BETWEEN_LINES
    
    temp_panel_path = os.path.join(temp_dir, f"temp_panel_{panel_num}.jpg")
    base_image.save(temp_panel_path, "jpeg", quality=95)
    return temp_panel_path, None


def assemble_composite_image(panel_filenames, output_path):
    """Creates the final 4-up composite image."""
    try:
        images = [Image.open(fp) for fp in panel_filenames]
        composite_image = Image.new('RGB', (1080, 1350), 'white')
        draw = ImageDraw.Draw(composite_image)
        try:
            header_font = ImageFont.truetype(TITLEFONT_PATH, HEADER_FONT_SIZE)
            draw.text((14, HEADER_HEIGHT / 2), HEADER_TEXT, font=header_font, fill=HEADER_TEXT_COLOR, anchor='lm')
        except Exception as e:
            print(f"Could not draw header on composite image: {e}")
        
        composite_image.paste(images[0], (14, 40))
        composite_image.paste(images[1], (546, 40))
        composite_image.paste(images[2], (14, 697))
        composite_image.paste(images[3], (546, 697))
        composite_image.save(output_path, "jpeg", quality=95)
        return True, None
    except Exception as e:
        return False, f"Error assembling composite image: {e}"


def _generate_images(script_text):
    """Shared logic for preview and final generation."""
    panel_data, error = process_script(script_text)
    if error:
        return None, None, error

    temp_dir = tempfile.mkdtemp()
    temp_panel_paths = []
    for i, panel in enumerate(panel_data):
        path, error = create_panel_image(panel['image_path'], panel['dialogue'], i, temp_dir)
        if error:
            import shutil
            shutil.rmtree(temp_dir)
            return None, None, error
        temp_panel_paths.append(path)

    return temp_panel_paths, temp_dir, None


def generate_preview_image(comic_script_text):
    """Generates a single in-memory composite preview image."""
    temp_panel_paths, temp_dir, error = _generate_images(comic_script_text)
    if error:
        return None, error
    if not temp_panel_paths:
        return None, "Failed to generate panel paths for preview."

    try:
        composite_preview_path = os.path.join(temp_dir, "preview_composite.jpg")
        success, error = assemble_composite_image(temp_panel_paths, composite_preview_path)
        if not success:
            return None, error
        with Image.open(composite_preview_path) as img:
            return img.copy(), None
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def generate_comic_from_script_text(comic_script_text):
    """Generates 5 final JPG images from a block of script text."""
    temp_panel_paths, temp_dir, error = _generate_images(comic_script_text)
    if error:
        return None, error
    if not temp_panel_paths:
        return None, "Failed to generate panel paths for final output."

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        base_filename = f"{OUTPUT_FILENAME_PREFIX}{timestamp}"
        
        output_dir = "Output_Comics"
        os.makedirs(output_dir, exist_ok=True)
        
        output_paths = []
        for i, temp_panel_path in enumerate(temp_panel_paths):
            full_size_path = os.path.join(output_dir, f"{base_filename}_panel_{i+1}.jpg")
            panel_img = Image.open(temp_panel_path)
            full_size_panel = panel_img.resize((1080, 1350), Image.Resampling.LANCZOS)
            full_size_panel.save(full_size_path, "jpeg", quality=95)
            output_paths.append(full_size_path)

        composite_path = os.path.join(output_dir, f"{base_filename}_composite.jpg")
        success, error = assemble_composite_image(temp_panel_paths, composite_path)
        if not success:
            return None, error
        output_paths.append(composite_path)

        return output_paths, None
    except Exception as e:
        return None, f"Error during final image generation: {e}"
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
