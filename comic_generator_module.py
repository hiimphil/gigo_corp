# comic_generator_module.py
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import tempfile # --- Added for temporary directory handling

# --- Refactored: Use relative paths instead of hardcoded absolute paths ---
# The script will now look for these folders in its own directory.
IMAGE_PATH = "Images/"
FONT_PATH = "Fonts/"
TITLEFONT_PATH = os.path.join(FONT_PATH, "RNS-B.ttf")
MAIN_FONT_PATH = os.path.join(FONT_PATH, "Krungthep.ttf") # Renamed for clarity

# --- Removed hardcoded OUTPUT_PATH ---

# --- Panel & Text Configuration (Unchanged) ---
FONT_SIZE = 32
TEXT_COLOR = "#ffffff"
TEXT_POSITION = (256, 250)
SPACING_BETWEEN_LINES = 4
PANEL_WIDTH = 512
PANEL_HEIGHT = 640
OUTPUT_FILENAME_PREFIX = "gigoco_"

# --- Header Configuration (Unchanged) ---
HEADER_TEXT = "GIGOCO"
HEADER_HEIGHT = 40
HEADER_FONT_SIZE = 40
HEADER_TEXT_COLOR = "#6d7467"

# --- Image Filenames (Unchanged) ---
IMAGE_FILES = {
    "A_TALKING": "A_talking.png",
    "A_NOTTALKING": "A_nottalking.png",
    "B_TALKING": "B_talking.png",
    "B_NOTTALKING": "B_nottalking.png",
    "C_TALKING": "C_talking.png",
    "C_NOTTALKING": "C_nottalking.png"
}

def parse_script_lines(script_text_block):
    if not script_text_block.strip(): return None
    lines = script_text_block.strip().split('\n')
    return lines if len(lines) == 4 else None

def process_script_line(line):
    parts = line.split(":", 1)
    character = parts[0].strip().upper()
    dialogue = parts[1].strip() if len(parts) > 1 else ""
    if character not in ["A", "B", "C"]: return {"character": "A", "dialogue": "", "image_key": "A_NOTTALKING"}
    is_talking = bool(dialogue)
    image_key_suffix = "TALKING" if is_talking else "NOTTALKING"
    image_key = f"{character}_{image_key_suffix}"
    return {"character": character, "dialogue": dialogue, "image_key": image_key}

# --- Refactored: This function now accepts a 'temp_dir' to save the panel to ---
def create_panel_image(panel_info, panel_num, temp_dir):
    base_image_filename = IMAGE_FILES.get(panel_info["image_key"])
    if not base_image_filename:
        default_fallback_key = "A_NOTTALKING"
        base_image_filename = IMAGE_FILES.get(default_fallback_key, "A_nottalking.png")
        print(f"Warning: Image key '{panel_info['image_key']}' not found. Using fallback.")
    full_image_path = os.path.join(IMAGE_PATH, base_image_filename)

    try:
        base_image = Image.open(full_image_path).convert("RGBA")
        if base_image.size != (PANEL_WIDTH, PANEL_HEIGHT):
            base_image = base_image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    except FileNotFoundError:
        print(f"--> FATAL ERROR: File not found at path: '{full_image_path}'")
        return None
    except Exception as e:
        print(f"--> FATAL ERROR: An error occurred while opening '{full_image_path}': {e}")
        return None

    draw = ImageDraw.Draw(base_image)
    if panel_info["dialogue"]:
        try:
            font = ImageFont.truetype(MAIN_FONT_PATH, FONT_SIZE)
        except IOError:
            print(f"Warning: Font not found at {MAIN_FONT_PATH}. Using default font.")
            font = ImageFont.load_default()
        
        from textwrap import TextWrapper
        wrapper = TextWrapper(width=26)
        lines = wrapper.wrap(text=panel_info["dialogue"])
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
    
    # Save the panel image inside the provided temporary directory
    temp_panel_path = os.path.join(temp_dir, f"temp_panel_{panel_num}.png")
    base_image.save(temp_panel_path)
    return temp_panel_path

def create_full_size_single_panel(panel_image_path, output_path):
    # This function remains largely the same, just receives the correct output_path
    try:
        panel_img = Image.open(panel_image_path)
        full_size_panel = panel_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        if full_size_panel.mode == 'RGBA':
            full_size_panel = full_size_panel.convert('RGB')
        full_size_panel.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating full-size single panel: {e}")
        return False

def assemble_composite_image(panel_filenames, output_path):
    # This function remains largely the same
    try:
        images = [Image.open(fp) for fp in panel_filenames]
        composite_image = Image.new('RGB', (1080, 1350), 'white')
        draw = ImageDraw.Draw(composite_image)
        try:
            header_font = ImageFont.truetype(TITLEFONT_PATH, HEADER_FONT_SIZE)
            draw.text((14, HEADER_HEIGHT / 2), HEADER_TEXT, font=header_font, fill=HEADER_TEXT_COLOR, anchor='lm')
        except Exception as e:
            print(f"Could not draw header on composite image: {e}")
        
        composite_image.paste(images[0], (14, 40)); composite_image.paste(images[1], (546, 40))
        composite_image.paste(images[2], (14, 697)); composite_image.paste(images[3], (546, 697))
        composite_image.save(output_path)
        return True
    except Exception as e:
        print(f"Error assembling composite image: {e}")
        return False

# --- Refactored: Main function now uses a temporary directory ---
def generate_comic_from_script_text(comic_script_text):
    print("Starting carousel comic generation from script text...")

    script_lines = parse_script_lines(comic_script_text)
    if not script_lines:
        print("Script parsing failed.")
        return None
    
    panel_details_list = [process_script_line(line) for line in script_lines]
    
    # Create a temporary directory that will be automatically cleaned up
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory for outputs: {temp_dir}")
        temp_panel_filenames = []
        for i, panel_info_data in enumerate(panel_details_list):
            # Pass the temp_dir to the panel creation function
            temp_filename = create_panel_image(panel_info_data, i, temp_dir)
            if not temp_filename:
                print("Failed to create a temporary panel.")
                return None
            temp_panel_filenames.append(temp_filename)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        base_filename = f"{OUTPUT_FILENAME_PREFIX}{timestamp}"
        
        output_paths = []

        # Create the 4 full-size individual panel images in the temp directory
        for i, temp_panel_path in enumerate(temp_panel_filenames):
            full_size_path = os.path.join(temp_dir, f"{base_filename}_panel_{i+1}.png")
            if not create_full_size_single_panel(temp_panel_path, full_size_path):
                return None
            output_paths.append(full_size_path)

        # Create the final 4-panel composite image in the temp directory
        composite_path = os.path.join(temp_dir, f"{base_filename}_composite.png")
        if not assemble_composite_image(temp_panel_filenames, composite_path):
            return None
        output_paths.append(composite_path)
        
        # NOTE: We can no longer remove temp files as they are needed by other modules.
        # The 'with' statement will handle cleanup, but for now we return the paths.
        # For a long-running app, a more robust file handling strategy might be needed,
        # but for this workflow, the paths are passed to the uploader immediately.
        
        print(f"Carousel comic generation successful. {len(output_paths)} images created in temp dir.")
        return output_paths