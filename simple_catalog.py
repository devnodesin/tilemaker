from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import math
import argparse
import time

def parse_args():
    parser = argparse.ArgumentParser(description='Generate PDF product catalog from images')
    parser.add_argument('input_image_path', 
                        help='Directory containing product images')
    parser.add_argument('--out', 
                        default=None,
                        help='Output PDF file path (default: out/product_catalog_{timestamp}.pdf)')
    parser.add_argument('--rows', 
                        type=int,
                        default=3,
                        help='Number of rows per page (default: 3)')
    parser.add_argument('--cols', 
                        type=int,
                        default=3,
                        help='Number of columns per page (default: 3)')
    parser.add_argument('--compress',
                        type=float,
                        default=None,
                        help='Target maximum PDF file size in MB (best effort, e.g. 2 for 2MB)')
    return parser.parse_args()

# Paths and configuration
args = parse_args()
image_dir = args.input_image_path

# Set output PDF path with timestamp if not provided
if args.out:
    output_pdf = f"out/{args.out}.pdf"
    if not output_pdf.lower().endswith('.pdf'):
        output_pdf += '.pdf'
else:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_pdf = f"out/simple_catalog_{timestamp}.pdf"

images_per_row = args.cols
rows_per_page = args.rows
images_per_page = images_per_row * rows_per_page
row_spacing = 40  # Space between rows
page_width, page_height = letter
margin = 50
spacing = 10

# Header configuration
header_text = "Deltaware.in - Parking Tiles Catalog - Whatsapp: 9940198130"
header_font_size = 14
header_margin = 100

# Create a PDF canvas
c = canvas.Canvas(output_pdf, pagesize=letter)

# Get image files
image_files = [f for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
image_files.sort()

# Image dimensions for placement
usable_width = page_width - 2 * margin
usable_height = page_height - header_margin - margin  # Adjust usable height to account for header and bottom margin
image_width = (usable_width - (images_per_row - 1) * spacing) / images_per_row
image_height = (usable_height - (rows_per_page - 1) * row_spacing) / rows_per_page

font_size = 10
temp_files = []  # Track temporary files for cleanup

# Set image quality based on compress argument
if args.compress:
    image_quality = 25  # Lower quality for smaller file size
else:
    image_quality = 85  # Default quality

# Calculate total pages
total_pages = math.ceil(len(image_files) / images_per_page)

for page_num in range(total_pages):
    start_idx = page_num * images_per_page
    end_idx = start_idx + images_per_page
    page_images = image_files[start_idx:end_idx]

    # Add header
    c.setFont("Helvetica-Bold", header_font_size)
    c.drawString(margin, page_height - margin, header_text)    

    # Add page number
    c.setFont("Helvetica", 8)
    c.drawString(page_width/2, margin/2, f"Page {page_num + 1} of {total_pages}")

    for j, image_file in enumerate(page_images):
        try:
            # Calculate position with increased row spacing
            col = j % images_per_row
            row = j // images_per_row
            x = margin + col * (image_width + spacing)
            y = page_height - header_margin - row * (image_height + row_spacing)

            # Draw image
            img_path = os.path.join(image_dir, image_file)
            img = Image.open(img_path)

            # Calculate scaling factor to fit image inside the cell, preserving aspect ratio
            iw, ih = img.size
            scale = min(image_width / iw, image_height / ih, 1.0)
            draw_w = iw * scale
            draw_h = ih * scale

            # Center the image in the cell
            draw_x = x + (image_width - draw_w) / 2
            draw_y = y - image_height + (image_height - draw_h) / 2

            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            temp_file = os.path.join(os.environ["TEMP"], f"resized_{start_idx + j}.jpg") if os.name == 'nt' else os.path.join("/tmp", f"resized_{start_idx + j}.jpg")
            img.save(temp_file, quality=image_quality, optimize=True)
            temp_files.append(temp_file)

            c.drawImage(temp_file, draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=True, anchor='c')

            # Add product name
            product_name = os.path.splitext(image_file)[0]
            c.setFont("Helvetica-Bold", font_size)
            label_width = c.stringWidth(product_name, "Helvetica-Bold", font_size)
            label_x = x + (image_width - label_width) / 2
            label_y = y - image_height - 15
            c.drawString(label_x, label_y, product_name)
            
        except Exception as e:
            print(f"Error processing image {image_file}: {str(e)}")
            continue

    c.showPage()

# Save the PDF (only once)
c.save()

# Cleanup temporary files
for temp_file in temp_files:
    try:
        os.remove(temp_file)
    except:
        pass

print(f"Product catalog created: {output_pdf}")