from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import math
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Generate PDF product catalog from images')
    parser.add_argument('--img', 
                       default="./images/mcl/parking",
                       help='Directory containing product images')
    return parser.parse_args()

# Paths and configuration
args = parse_args()
image_dir = args.img
output_pdf = "out/product_catalog.pdf"
images_per_page = 9
images_per_row = 3
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
usable_height = page_height - 2 * margin
image_width = (usable_width - (images_per_row - 1) * spacing) / images_per_row
image_height = image_width
rows_per_page = images_per_page // images_per_row

font_size = 10
temp_files = []  # Track temporary files for cleanup

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
        # Calculate position with increased row spacing
        col = j % images_per_row
        row = j // images_per_row
        x = margin + col * (image_width + spacing)
        y = page_height - header_margin - (row * (image_height + row_spacing))

        # Draw image
        img_path = os.path.join(image_dir, image_file)
        img = Image.open(img_path)
        img.thumbnail((image_width, image_height))
        
        temp_file = os.path.join(os.environ["TEMP"], f"resized_{start_idx + j}.jpg") if os.name == 'nt' else os.path.join("/tmp", f"resized_{start_idx + j}.jpg")
        img.save(temp_file)
        temp_files.append(temp_file)

        c.drawImage(temp_file, x, y - image_height, image_width, image_height)

        # Add product name
        product_name = os.path.splitext(image_file)[0]
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(x, y - image_height - 15, product_name)

    c.showPage()

# Save the PDF
c.save()

# Cleanup temporary files
for temp_file in temp_files:
    try:
        os.remove(temp_file)
    except:
        pass

print(f"Product catalog created: {output_pdf}")