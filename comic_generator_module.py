# comic_generator_module.py
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import tempfile
from textwrap import TextWrapper
import re # Import the regular expression module

# --- Configuration ---
IMAGE_PATH = "Images/"
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

IMAGE_FILES = {
    "A_TALKING": "A_talking.png",
    "A_NOTTALKING": "A_nottalking.png",
    "B_TALKING": "B_talking.png",
    "B_NOTTALKING": "B_nottalking.png",
    "C_TALKING": "C_talking.png",
    "C_NOTTALKING": "C_nottalking.png",
    "A_TALKING_LEFT": "A_talking_left.png",
    "A_NOTTALKING_LEFT": "A_nottalking_left.png",
    "B_SURPRISED": "B_surprised.png",
    "D_NOTTALKING": "D_nottalking.png",
    "D_WAVING": "D_waving.png",
    "A_NOTTALKING_D": "A_nottalking_D.png",
    "A_TALKING_D": "A_talking_D.png",
    "B_NOTTALKING_D": "B_nottalking_D.png",
    "B_TALKING_D": "B_talking_D.png"
}
# --- End Configuration ---


def parse_script_lines(script_text_block):
    """Parses a block of text into exactly 4 lines."""
    if not script_text_block.strip(): return None
    lines = script_text_block.strip().split('\n')
    return lines if len(lines) == 4 else None


def create_panel_image(image_key, dialogue, panel_num, temp_dir):
    """Creates a single panel image with dialogue text."""
    image_filename = IMAGE_FILES.get(image_key)
    if not image_filename:
        print(f"Warning: Image key '{image_key}' not found. Using fallback.")
        image_filename = IMAGE_FILES["A_NOTTALKING"]

    full_image_path = os.path.join(IMAGE_PATH, image_filename)
    
    if not os.path.exists(full_image_path):
        print(f"--> FATAL ERROR: IMAGE NOT FOUND AT: {full_image_path}")
        return None

    try:
        base_image = Image.open(full_image_path).convert("RGBA")
        if base_image.size != (PANEL_WIDTH, PANEL_HEIGHT):
            base_image = base_image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"--> FATAL ERROR: An error occurred while opening '{full_image_path}': {e}")
        return None

    draw = ImageDraw.Draw(base_image)

    # The dialogue passed to this function is now pre-cleaned.
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
    
    final_image = base_image.convert("RGB")
    temp_panel_path = os.path.join(temp_dir, f"temp_panel_{panel_num}.jpg")
    final_image.save(temp_panel_path, "jpeg")
    return temp_panel_path


def process_script(script_lines):
    """
    Processes a list of script lines to determine the final image and dialogue for each panel.
    This function contains all the conditional logic.
    """
    panel_details_list = []
    previous_character = None

    for line in script_lines:
        parts = line.split(":", 1)
        if len(parts) < 2:
            panel_details_list.append({"image_key": "A_NOTTALKING", "dialogue": line.strip()})
            previous_character = None
            continue

        character = parts[0].strip().upper()
        original_dialogue = parts[1].strip()
        
        if character not in ["A", "B", "C", "D"]:
            panel_details_list.append({"image_key": "A_NOTTALKING", "dialogue": original_dialogue})
            previous_character = None
            continue

        # 1. Determine final display text by removing actions in parentheses
        display_dialogue = re.sub(r"\(.*?\)", "", original_dialogue).strip()

        # 2. Determine base talking state
        is_talking = bool(display_dialogue)
        image_state = "TALKING" if is_talking else "NOTTALKING"
        image_key = f"{character}_{image_state}"

        # 3. Apply logic overrides based on the *original* dialogue in order of priority
        #    This has been reordered to prioritize the directional (d) cue.
        if character == 'D' and "(waving)" in original_dialogue.lower():
            image_key = 'D_WAVING'
        elif character in ['A', 'B'] and "(d)" in original_dialogue.lower():
            image_key = f"{character}_{image_state}_D"
        elif character == 'B' and "!" in original_dialogue:
            image_key = 'B_SURPRISED'
        elif character == 'A' and previous_character == 'C':
            image_key = 'A_TALKING_LEFT' if is_talking else 'A_NOTTALKING_LEFT'

        panel_details_list.append({"image_key": image_key, "dialogue": display_dialogue})
        previous_character = character
        
    return panel_details_list


def create_full_size_single_panel(panel_image_path, output_path):
    """Creates a 1080x1350 image by resizing a panel."""
    try:
        panel_img = Image.open(panel_image_path)
        full_size_panel = panel_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        full_size_panel.save(output_path, "jpeg")
        return True
    except Exception as e:
        print(f"Error creating full-size single panel: {e}")
        return False


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
        composite_image.save(output_path, "jpeg")
        return True
    except Exception as e:
        print(f"Error assembling composite image: {e}")
        return False


def _generate_images_from_panel_data(panel_details_list, temp_dir):
    """Helper function to create all image files from a list of panel details."""
    temp_panel_filenames = []
    for i, panel_info in enumerate(panel_details_list):
        temp_filename = create_panel_image(
            image_key=panel_info['image_key'],
            dialogue=panel_info['dialogue'],
            panel_num=i,
            temp_dir=temp_dir
        )
        if not temp_filename:
            return None, None
        temp_panel_filenames.append(temp_filename)
        
    composite_preview_path = os.path.join(temp_dir, "preview_composite.jpg")
    if not assemble_composite_image(temp_panel_filenames, composite_preview_path):
        return None, None

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_filename = f"{OUTPUT_FILENAME_PREFIX}{timestamp}"
    output_paths = []
    for i, temp_panel_path in enumerate(temp_panel_filenames):
        full_size_path = os.path.join(temp_dir, f"{base_filename}_panel_{i+1}.jpg")
        if not create_full_size_single_panel(temp_panel_path, full_size_path):
            return None, None
        output_paths.append(full_size_path)

    final_composite_path = os.path.join(temp_dir, f"{base_filename}_composite.jpg")
    if not assemble_composite_image(temp_panel_filenames, final_composite_path):
        return None, None
    output_paths.append(final_composite_path)

    return composite_preview_path, output_paths


def generate_preview_image(comic_script_text):
    """Generates a single in-memory composite preview image as JPG."""
    script_lines = parse_script_lines(comic_script_text)
    if not script_lines: return None

    panel_details_list = process_script(script_lines)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        composite_path, _ = _generate_images_from_panel_data(panel_details_list, temp_dir)
        if not composite_path:
            return None
        with Image.open(composite_path) as img:
            return img.copy()


def generate_comic_from_script_text(comic_script_text):
    """Generates 5 final JPG images from a block of script text."""
    script_lines = parse_script_lines(comic_script_text)
    if not script_lines: return None

    panel_details_list = process_script(script_lines)

    temp_dir = tempfile.mkdtemp()
    _, output_paths = _generate_images_from_panel_data(panel_details_list, temp_dir)
    
    if not output_paths:
        return None
    
    return output_paths
