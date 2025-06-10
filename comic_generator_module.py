# comic_generator_module.py
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import tempfile

# --- Use relative paths ---
IMAGE_PATH = "Images/"
FONT_PATH = "Fonts/"
TITLEFONT_PATH = os.path.join(FONT_PATH, "RNS-B.ttf")
MAIN_FONT_PATH = os.path.join(FONT_PATH, "Krungthep.ttf")

# --- Configuration (Unchanged) ---
# ... (rest of the configuration remains the same) ...
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
IMAGE_FILES = {
    "A_TALKING": "A_talking.png",
    "A_NOTTALKING": "A_nottalking.png",
    "B_TALKING": "B_talking.png",
    "B_NOTTALKING": "B_nottalking.png",
    "C_TALKING": "C_talking.png",
    "C_NOTTALKING": "C_nottalking.png"
}
# --- End of Configuration ---

def parse_script_lines(script_text_block):
    if not script_text_block.strip(): return None
    lines = script_text_block.strip().split('\n')
    return lines if len(lines) == 4 else None

def process_script_line(line):
    # ... (this function is fine, no changes needed) ...
    parts = line.split(":", 1)
    character = parts[0].strip().upper()
    dialogue = parts[1].strip() if len(parts) > 1 else ""
    if character not in ["A", "B", "C"]: return {"character": "A", "dialogue": "", "image_key": "A_NOTTALKING"}
    is_talking = bool(dialogue)
    image_key_suffix = "TALKING" if is_talking else "NOTTALKING"
    image_key = f"{character}_{image_key_suffix}"
    return {"character": character, "dialogue": dialogue, "image_key": image_key}


def create_panel_image(panel_info, panel_num, temp_dir):
    base_image_filename = IMAGE_FILES.get(panel_info["image_key"])
    full_image_path = os.path.join(IMAGE_PATH, base_image_filename)

    # --- ENHANCED LOGGING ---
    print(f"--- Creating Panel {panel_num+1} ---")
    print(f"Attempting to load image: '{full_image_path}'")
    if not os.path.exists(full_image_path):
        print(f"--> FATAL ERROR: IMAGE NOT FOUND AT: {full_image_path}")
        return None
    print("Image file found.")
    # --- END LOGGING ---

    try:
        base_image = Image.open(full_image_path).convert("RGBA")
        if base_image.size != (PANEL_WIDTH, PANEL_HEIGHT):
            base_image = base_image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"--> FATAL ERROR: An error occurred while opening '{full_image_path}': {e}")
        return None

    draw = ImageDraw.Draw(base_image)
    if panel_info["dialogue"]:
        # --- ENHANCED LOGGING ---
        print(f"Attempting to load font: '{MAIN_FONT_PATH}'")
        if not os.path.exists(MAIN_FONT_PATH):
            print(f"--> FATAL ERROR: FONT NOT FOUND AT: {MAIN_FONT_PATH}")
            # Fallback to default font to avoid crashing, but the error is logged.
            font = ImageFont.load_default()
        else:
            print("Font file found.")
            font = ImageFont.truetype(MAIN_FONT_PATH, FONT_SIZE)
        # --- END LOGGING ---
        
        from textwrap import TextWrapper
        wrapper = TextWrapper(width=26)
        # ... (rest of text drawing logic is fine) ...
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

    temp_panel_path = os.path.join(temp_dir, f"temp_panel_{panel_num}.png")
    base_image.save(temp_panel_path)
    print(f"Successfully created panel {panel_num+1}.")
    return temp_panel_path

# ... (create_full_size_single_panel and assemble_composite_image are fine) ...
def create_full_size_single_panel(panel_image_path, output_path):
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
    try:
        images = [Image.open(fp) for fp in panel_filenames]
        composite_image = Image.new('RGB', (1080, 1350), 'white')
        draw = ImageDraw.Draw(composite_image)
        # --- ENHANCED LOGGING ---
        print(f"Attempting to load title font: '{TITLEFONT_PATH}'")
        if not os.path.exists(TITLEFONT_PATH):
            print(f"--> WARNING: Title font not found at {TITLEFONT_PATH}, skipping header text.")
        else:
            print("Title font found.")
            header_font = ImageFont.truetype(TITLEFONT_PATH, HEADER_FONT_SIZE)
            draw.text((14, HEADER_HEIGHT / 2), HEADER_TEXT, font=header_font, fill=HEADER_TEXT_COLOR, anchor='lm')
        # --- END LOGGING ---
        
        composite_image.paste(images[0], (14, 40)); composite_image.paste(images[1], (546, 40))
        composite_image.paste(images[2], (14, 697)); composite_image.paste(images[3], (546, 697))
        composite_image.save(output_path)
        return True
    except Exception as e:
        print(f"Error assembling composite image: {e}")
        return False


# Updated

def generate_comic_from_script_text(comic_script_text):
    print("--- DIAGNOSTICS ---")
    cwd = os.getcwd()
    print(f"Current Working Directory: {cwd}")
    print(f"Contents of CWD: {os.listdir('.')}")
    print(f"Checking for Images folder: Exists = {os.path.exists('Images')}")
    if os.path.exists('Images'): print(f"Contents of Images: {os.listdir('Images')}")
    print(f"Checking for Fonts folder: Exists = {os.path.exists('Fonts')}")
    if os.path.exists('Fonts'): print(f"Contents of Fonts: {os.listdir('Fonts')}")
    print("--- END DIAGNOSTICS ---")

    print("Starting carousel comic generation from script text...")

    script_lines = parse_script_lines(comic_script_text)
    if not script_lines:
        print("Script parsing failed.")
        return None
    
    panel_details_list = [process_script_line(line) for line in script_lines]
    
    # --- MODIFICATION: Create a temp directory that is NOT automatically deleted ---
    temp_dir = tempfile.mkdtemp()
    print(f"Created persistent temporary directory for this session: {temp_dir}")
    
    temp_panel_filenames = []
    for i, panel_info_data in enumerate(panel_details_list):
        temp_filename = create_panel_image(panel_info_data, i, temp_dir)
        if not temp_filename:
            print("Failed to create a temporary panel.")
            return None
        temp_panel_filenames.append(temp_filename)

    if not temp_panel_filenames:
            print("No panels were generated, returning None.")
            return None

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_filename = f"{OUTPUT_FILENAME_PREFIX}{timestamp}"
    output_paths = []

    for i, temp_panel_path in enumerate(temp_panel_filenames):
        full_size_path = os.path.join(temp_dir, f"{base_filename}_panel_{i+1}.png")
        if not create_full_size_single_panel(temp_panel_path, full_size_path):
            return None
        output_paths.append(full_size_path)

    composite_path = os.path.join(temp_dir, f"{base_filename}_composite.png")
    if not assemble_composite_image(temp_panel_filenames, composite_path):
        return None
    output_paths.append(composite_path)
    
    print(f"Carousel comic generation successful. {len(output_paths)} images created in temp dir.")
    return output_paths