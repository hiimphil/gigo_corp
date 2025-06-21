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
        return None, None, line # Return the line as dialogue if it doesn't match
    
    character = match.group(1).upper()
    action = match.group(2) or "normal" # Default action/emotion is 'normal'
    dialogue = match.group(3).strip()
    
    return character, action.lower(), dialogue


def determine_direction(current_char, prev_char):
    """Determines which way the character should be looking based on specific rules."""
    # Character C is always facing Right.
    if current_char == 'C':
        return "Right"
        
    # Character B's default is Left.
    if current_char == 'B':
        return "Left"
        
    # Character A's logic: defaults Right, but turns Left for C.
    if current_char == 'A':
        if prev_char == 'C':
            return "Left"
        else:
            return "Right"
            
    # Default direction for any other character (like D) or initial panel.
    return "Right"


def find_image_path(character, direction, talking_state, action):
    """
    Builds a path to an image folder and selects a random image.
    Includes robust fallbacks for missing folders.
    """
    # 1. Build a list of potential paths in order of preference.
    paths_to_try = []
    opposite_direction = "Left" if direction == "Right" else "Right"
    opposite_talking_state = "Nottalking" if talking_state == "Talking" else "Talking"

    # Tier 1: The most specific path possible.
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, talking_state, action))
    # Tier 2: The 'normal' action in the correct direction.
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, talking_state, "normal"))
    # Tier 3: The 'normal' action in the opposite direction (if primary direction folder doesn't exist).
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, opposite_direction, talking_state, "normal"))
    # Tier 4: The 'normal' action in the correct direction but opposite talking state (last resort).
    paths_to_try.append(os.path.join(IMAGE_BASE_PATH, character, direction, opposite_talking_state, "normal"))

    # 2. Iterate through the paths and find the first valid one with images.
    for path in paths_to_try:
        if os.path.isdir(path):
            try:
                images = [f for f in os.listdir(path) if f.lower().endswith('.jpg')]
                if images:
                    print(f"Success: Found image in '{path}'")
                    return os.path.join(path, random.choice(images))
            except Exception as e:
                print(f"--> WARNING: Could not read directory '{path}': {e}")
                continue
    
    # 3. If no path was found, return None.
    print(f"--> FATAL ERROR: Could not find any valid image for character '{character}'")
    return None


def process_script(script_text):
    """
    Processes a full script and returns a list of panel data
    containing image paths and dialogue.
    """
    panel_data = []
    previous_character = None
    lines = script_text.strip().split('\n')
    
    if len(lines) != 4:
        return None # Script must have 4 lines

    for line in lines:
        character, action, dialogue = parse_script_line(line)
        if not character:
            print(f"Warning: Could not parse line: '{line}'")
            continue

        direction = determine_direction(character, previous_character)
        talking_state = "Talking" if dialogue else "Nottalking"
        
        image_path = find_image_path(character, direction, talking_state, action)
        
        if not image_path:
            print(f"FATAL: Could not find any image for line: '{line}'")
            return None 

        panel_data.append({"image_path": image_path, "dialogue": dialogue})
        previous_character = character
        
    return panel_data


def create_panel_image(image_path, dialogue, panel_num, temp_dir):
    """Creates a single panel image with dialogue text."""
    try:
        base_image = Image.open(image_path).convert("RGB") # Open as RGB for JPG
        if base_image.size != (PANEL_WIDTH, PANEL_HEIGHT):
            base_image = base_image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"--> FATAL ERROR: Could not open or resize image '{image_path}': {e}")
        return None

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
            line_width = line_bbox[2] - line_bbox[0]
            x_text = (PANEL_WIDTH - line_width) / 2
            draw.text((x_text, y_text), line, font=font, fill=TEXT_COLOR)
            y_text += line_height + SPACING_BETWEEN_LINES
    
    temp_panel_path = os.path.join(temp_dir, f"temp_panel_{panel_num}.jpg")
    base_image.save(temp_panel_path, "jpeg", quality=95)
    return temp_panel_path


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
        return True
    except Exception as e:
        print(f"Error assembling composite image: {e}")
        return False


def _generate_images(script_text):
    """Shared logic for preview and final generation."""
    panel_data = process_script(script_text)
    if not panel_data:
        return None, None

    temp_dir = tempfile.mkdtemp()
    temp_panel_paths = []
    for i, panel in enumerate(panel_data):
        path = create_panel_image(panel['image_path'], panel['dialogue'], i, temp_dir)
        if not path:
            return None, None
        temp_panel_paths.append(path)

    return temp_panel_paths, temp_dir


def generate_preview_image(comic_script_text):
    """Generates a single in-memory composite preview image."""
    temp_panel_paths, temp_dir = _generate_images(comic_script_text)
    if not temp_panel_paths:
        return None

    try:
        composite_preview_path = os.path.join(temp_dir, "preview_composite.jpg")
        if not assemble_composite_image(temp_panel_paths, composite_preview_path):
            return None
        with Image.open(composite_preview_path) as img:
            return img.copy()
    finally:
        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def generate_comic_from_script_text(comic_script_text):
    """Generates 5 final JPG images from a block of script text."""
    temp_panel_paths, temp_dir = _generate_images(comic_script_text)
    if not temp_panel_paths:
        return None

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        base_filename = f"{OUTPUT_FILENAME_PREFIX}{timestamp}"
        
        output_paths = []

        # Create the four full-size panels
        for i, temp_panel_path in enumerate(temp_panel_paths):
            full_size_path = os.path.join(temp_dir, f"{base_filename}_panel_{i+1}.jpg")
            panel_img = Image.open(temp_panel_path)
            full_size_panel = panel_img.resize((1080, 1350), Image.Resampling.LANCZOS)
            full_size_panel.save(full_size_path, "jpeg", quality=95)
            output_paths.append(full_size_path)

        # Create the final composite image
        composite_path = os.path.join(temp_dir, f"{base_filename}_composite.jpg")
        if not assemble_composite_image(temp_panel_paths, composite_path):
            return None
        output_paths.append(composite_path)

        return output_paths
    except Exception as e:
        print(f"Error during final image generation: {e}")
        return None
    # Note: We are not cleaning up the temp_dir here because the main app needs
    # access to the files for uploading. A more advanced app might handle this differently.
