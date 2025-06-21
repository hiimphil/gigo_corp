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


def parse_script_line(line):
    """Parses a single line into its character, action, and dialogue components."""
    match = re.match(r"^\s*([A-D]):\s*(?:\((.*?)\))?\s*(.*)", line, re.IGNORECASE)
    if not match:
        return None, None, line
    
    character = match.group(1).upper()
    action = match.group(2) or "normal"
    dialogue = match.group(3).strip()
    
    return character, action.lower(), dialogue


def determine_direction(current_char, prev_char):
    """Determines which way the character should be looking based on specific rules."""
    if current_char == 'C':
        return "Right"
    if current_char == 'B':
        return "Left"
    if current_char == 'A':
        return "Right" if prev_char != 'C' else "Left"
    return "Right"


def find_image_path(character, direction, talking_state, action):
    """Builds a path to an image folder, selects a random image, and returns an error if not found."""
    paths_to_try = []
    opposite_direction = "Left" if direction == "Right" else "Right"
    opposite_talking_state = "Nottalking" if talking_state == "Talking" else "Talking"

    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, talking_state, action))
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, talking_state, "normal"))
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, opposite_direction, talking_state, "normal"))
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, opposite_talking_state, "normal"))

    for path in paths_to_try:
        if os.path.isdir(path):
            try:
                images = [f for f in os.listdir(path) if f.lower().endswith('.jpg')]
                if images:
                    return os.path.join(path, random.choice(images)), None
            except Exception as e:
                print(f"--> WARNING: Could not read directory '{path}': {e}")
                continue
    
    error_msg = f"No valid image found for Character: {character}, Direction: {direction}, State: {talking_state}, Action: {action}"
    return None, error_msg


def process_script(script_text):
    """Processes a script and returns panel data or an error message."""
    panel_data = []
    previous_character = None
    lines = script_text.strip().split('\n')
    
    if len(lines) != 4:
        return None, "Script must have exactly 4 lines."

    for line in lines:
        character, action, dialogue = parse_script_line(line)
        if not character:
            return None, f"Could not parse line: '{line}'"

        direction = determine_direction(character, previous_character)
        talking_state = "Talking" if dialogue else "Nottalking"
        
        image_path, error = find_image_path(character, direction, talking_state, action)
        if error:
            return None, f"Error on line '{line}': {error}"

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
        
        output_paths = []
        for i, temp_panel_path in enumerate(temp_panel_paths):
            full_size_path = os.path.join(temp_dir, f"{base_filename}_panel_{i+1}.jpg")
            panel_img = Image.open(temp_panel_path)
            full_size_panel = panel_img.resize((1080, 1350), Image.Resampling.LANCZOS)
            full_size_panel.save(full_size_path, "jpeg", quality=95)
            output_paths.append(full_size_path)

        composite_path = os.path.join(temp_dir, f"{base_filename}_composite.jpg")
        success, error = assemble_composite_image(temp_panel_paths, composite_path)
        if not success:
            return None, error
        output_paths.append(composite_path)

        return output_paths, None
    except Exception as e:
        return None, f"Error during final image generation: {e}"
