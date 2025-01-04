from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
import json
import argparse
from dataclasses import dataclass

@dataclass
class LayoutConfig:
    page_width: float
    page_height: float
    page_margin: int = 50
    header_font_size: int = 14
    header_margin: int = 75
    row_spacing: int = 25
    images_per_page: int = 9
    images_per_row: int = 3
    spacing: int = 10

def parse_args():
    parser = argparse.ArgumentParser(description='Generate PDF catalog from JSON config')
    parser.add_argument('--config', default="catalog/parking-tiles.json",
                       help='Path to catalog configuration JSON')
    return parser.parse_args()

def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return json.load(f)

def process_image(img_path: str, width: float, height: float) -> str | None:
    temp_path = os.path.join(os.environ["TEMP"], f"temp_{os.path.basename(img_path)}")
    try:
        img = Image.open(img_path)
        img.thumbnail((width, height))
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(temp_path)
        return temp_path
    except FileNotFoundError:
        print(f"Error: Image file not found: {img_path}")
        return None
    except Exception as e:
        print(f"Error processing image {img_path}: {str(e)}")
        return None

def draw_header(c, layout: LayoutConfig, title: str, page_num: int, total_pages: int):
    c.setFont("Helvetica-Bold", layout.header_font_size)
    c.drawString(layout.page_margin, layout.page_height - layout.page_margin, title)
    c.setLineWidth(1)
    c.line(layout.page_margin, layout.page_height - layout.header_margin + 20,
           layout.page_width - layout.page_margin, 
           layout.page_height - layout.header_margin + 20)
    c.setFont("Helvetica", 8)
    c.drawString(layout.page_width/2, layout.page_margin/2, 
                f"Page {page_num + 1} of {total_pages}")

def generate_catalog(config: dict, layout: LayoutConfig):
    os.makedirs(os.path.dirname(config['output_pdf']), exist_ok=True)
    c = canvas.Canvas(config['output_pdf'], pagesize=A4)
    temp_files = []

    # Calculate image dimensions
    usable_width = layout.page_width - 2 * layout.page_margin
    image_width = (usable_width - (layout.images_per_row - 1) * layout.spacing) / layout.images_per_row
    image_height = image_width

    for page_num, page_images in enumerate(config['pages']):
        draw_header(c, layout, config['title'], page_num, len(config['pages']))
        
        for idx, image_data in enumerate(page_images):
            # Calculate position
            col = idx % layout.images_per_row
            row = idx // layout.images_per_row
            x = layout.page_margin + col * (image_width + layout.spacing)
            y = (layout.page_height - layout.header_margin - 
                 (row * (image_height + layout.row_spacing)))

            # Handle image data format
            if isinstance(image_data, dict):
                image_file = image_data['file']
                image_title = image_data.get('title', os.path.splitext(image_file)[0])
            else:
                image_file = image_data
                image_title = os.path.splitext(image_data)[0]

            # Process and draw image
            img_path = os.path.join(config['image_path'], image_file)
            temp_file = process_image(img_path, image_width, image_height)
            temp_files.append(temp_file)
            
            c.drawImage(temp_file, x, y - image_height, image_width, image_height)
            c.setFont("Helvetica", 10)
            c.drawString(x, y - image_height - 15, image_title)
        
        c.showPage()
    
    c.save()
    cleanup_temp_files(temp_files)

def cleanup_temp_files(temp_files: list):
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except:
            pass

def main():
    args = parse_args()
    config = load_config(args.config)
    layout = LayoutConfig(page_width=A4[0], page_height=A4[1])
    generate_catalog(config, layout)
    print(f"Catalog generated: {config['output_pdf']}")

if __name__ == "__main__":
    main()