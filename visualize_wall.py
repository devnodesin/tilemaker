import os
import json
import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pathlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader

def create_wall_visualization(config):
    """Create wall tile visualizations based on the provided configuration."""
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(config['output_pdf']), exist_ok=True)
    
    # Create output directory for wall visualizations
    wall_output_dir = "./out/visual-wall"
    os.makedirs(wall_output_dir, exist_ok=True)
    
    # List to store paths of all generated images
    generated_images = []
    
    # Process each page in the configuration
    for page in config['pages']:
        # Create wall visualization for the page
        title = page['title']
        image_paths = [os.path.join(page['path'], img) for img in page['images']]
        padding = page.get('padding', 3)
        title_left_padding = page.get('title_padding', 30)  # New parameter for title left padding
        
        # Get footer images if available
        footer_images = []
        if 'footer' in page:
            footer_images = [os.path.join(page['path'], img) for img in page['footer']]
        
        # Now get the rows from the number of images and cols from the page config
        rows = len(image_paths)
        cols = page.get('cols', 5)
        
        # Load the first image to get dimensions
        if not image_paths:
            print(f"No images found for page {title}")
            continue
            
        try:
            first_image = Image.open(image_paths[0])
            img_width, img_height = first_image.size
            
            # Calculate the size of the output image with padding
            total_width = cols * img_width + (cols - 1) * padding
            total_height = rows * img_height + (rows - 1) * padding
            
            # Add extra height for footer and title
            footer_height = 0
            title_height = 50  # Height for title text (increased for 45px font)
            footer_spacing = 30  # Spacing between main visualization and title
            title_footer_spacing = 20  # Spacing between title and footer images
            footer_bottom_spacing = 30  # Spacing after footer section
            
            if footer_images:
                footer_img = Image.open(footer_images[0])
                footer_img_width, footer_img_height = footer_img.size
                footer_height = footer_img_height + title_footer_spacing + footer_bottom_spacing
            
            # Add space for title row and footer at the bottom
            final_height = total_height + footer_height + title_height + footer_spacing
            
            # Create a blank canvas
            wall_image = Image.new('RGB', (total_width, final_height), color='white')
            
            # Place the tiles on the canvas
            for row in range(rows):
                for col in range(cols):
                    # For the first column, use image from the images array based on row index
                    if col == 0:
                        img_path = image_paths[row]
                    # For other columns, always repeat the first image of the row
                    else:
                        img_path = image_paths[row]
                    
                    try:
                        img = Image.open(img_path)
                        x = col * (img_width + padding)
                        y = row * (img_height + padding)
                        wall_image.paste(img, (x, y))
                    except Exception as e:
                        print(f"Error processing image {img_path}: {e}")
            
            # Calculate positions for footer section
            title_start_y = total_height + footer_spacing
            footer_start_y = title_start_y + title_height + title_footer_spacing
            
            # Add title text first (above footer images)
            try:
                draw = ImageDraw.Draw(wall_image)
                # Try to use a system font with 45px size
                try:
                    font = ImageFont.truetype("arial.ttf", 45)
                except:
                    font = ImageFont.load_default()
                
                # Draw the title text on the left with the specified padding
                draw.text((title_left_padding, title_start_y), title, fill="black", font=font)
                
            except Exception as e:
                print(f"Error adding title text: {e}")
            
            # Add footer images with black border in their own row (below the title)
            if footer_images:
                footer_img = Image.open(footer_images[0])
                footer_img_width, footer_img_height = footer_img.size
                
                # Fixed spacing of 20px between footer images
                spacing = 20
                
                # Left align the footer images (start from the same left padding as title)
                start_x = title_left_padding
                
                for i, footer_path in enumerate(footer_images):
                    if i >= len(footer_images):
                        break  # Only show as many as available
                        
                    try:
                        footer_img = Image.open(footer_path)
                        # Add black border to footer image
                        border_width = 2
                        bordered_img = Image.new('RGB', 
                                              (footer_img_width + 2*border_width, 
                                              footer_img_height + 2*border_width), 
                                              color='white')
                        bordered_img.paste(footer_img, (border_width, border_width))
                        
                        x = start_x + i * (footer_img_width + spacing)
                        wall_image.paste(bordered_img, (x, footer_start_y))
                    except Exception as e:
                        print(f"Error processing footer image {footer_path}: {e}")
            
            # Save the visualization
            output_path = os.path.join(wall_output_dir, f"{title}.jpg")
            wall_image.save(output_path, quality=95)
            generated_images.append(output_path)
            print(f"Created wall visualization: {output_path}")
            
        except Exception as e:
            print(f"Error creating visualization for {title}: {e}")
            
    return generated_images

def generate_pdf(image_paths, pdf_path, compress=False, title=''):
    """Generate a PDF containing all the generated images (2 per page)."""
    try:
        # Create the PDF with A4 portrait orientation
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4  # A4 in portrait mode
        
        # Define margins (10px on each side)
        margin = 10
        usable_width = width - (2 * margin)
        usable_height = height - (2 * margin)
        
        # Reserve space for header and footer
        header_height = 30
        footer_height = 20
        
        # Calculate space available for images
        image_area_height = (usable_height - header_height - footer_height)
        # Each image gets half of the available space minus 5px spacing between images
        single_image_height = (image_area_height - 5) / 2
        
        # Process images two at a time
        for i in range(0, len(image_paths), 2):
            page_num = (i // 2) + 1
            
            # Add header with the page title
            c.setFont("Helvetica-Bold", 12)
            header_text = f"{title}"
            c.drawString(margin, height - margin - 15, header_text)
            
            # Add the first image
            img1_path = image_paths[i]
            img1 = Image.open(img1_path)
            
            # Compression if enabled
            if compress:
                new_size = (int(img1.width * 0.7), int(img1.height * 0.7))
                img1 = img1.resize(new_size, Image.LANCZOS)
                temp_path1 = f"{img1_path}_compressed.jpg"
                img1.save(temp_path1, "JPEG", quality=25)
                img1 = Image.open(temp_path1)
                img1_path = temp_path1
            
            # Calculate dimensions for the first image
            img1_width, img1_height = img1.size
            img1_ratio = img1_width / img1_height
            
            new_height1 = single_image_height
            new_width1 = new_height1 * img1_ratio
            if new_width1 > usable_width:
                new_width1 = usable_width
                new_height1 = new_width1 / img1_ratio
            
            # Position for first image (centered horizontally, at top of image area)
            x1 = margin + (usable_width - new_width1) / 2
            y1 = height - margin - header_height - new_height1
            
            c.drawImage(ImageReader(img1), x1, y1, width=new_width1, height=new_height1)
            
            # Clean up temp file if needed
            if compress and img1_path.endswith("_compressed.jpg"):
                try:
                    os.remove(img1_path)
                except:
                    pass
            
            # Add second image if available
            if i + 1 < len(image_paths):
                img2_path = image_paths[i + 1]
                img2 = Image.open(img2_path)
                
                # Compression if enabled
                if compress:
                    new_size = (int(img2.width * 0.7), int(img2.height * 0.7))
                    img2 = img2.resize(new_size, Image.LANCZOS)
                    temp_path2 = f"{img2_path}_compressed.jpg"
                    img2.save(temp_path2, "JPEG", quality=25)
                    img2 = Image.open(temp_path2)
                    img2_path = temp_path2
                
                # Calculate dimensions for second image
                img2_width, img2_height = img2.size
                img2_ratio = img2_width / img2_height
                
                new_height2 = single_image_height
                new_width2 = new_height2 * img2_ratio
                if new_width2 > usable_width:
                    new_width2 = usable_width
                    new_height2 = new_width2 / img2_ratio
                
                # Position for second image (centered horizontally, bottom of image area)
                x2 = margin + (usable_width - new_width2) / 2
                y2 = margin + footer_height
                
                c.drawImage(ImageReader(img2), x2, y2, width=new_width2, height=new_height2)
                
                # Clean up temp file if needed
                if compress and img2_path.endswith("_compressed.jpg"):
                    try:
                        os.remove(img2_path)
                    except:
                        pass
            
            # Add page number at bottom center
            c.setFont("Helvetica", 10)
            total_pages = (len(image_paths) + 1) // 2
            page_text = f"Page {page_num} of {total_pages}"
            text_width = c.stringWidth(page_text, "Helvetica", 10)
            c.drawString((width - text_width) / 2, margin + 5, page_text)
            
            # Add a new page if there are more images to come
            if i + 2 < len(image_paths):
                c.showPage()
        
        # Save the PDF
        c.save()
        print(f"Created PDF: {pdf_path}")
        
    except Exception as e:
        print(f"Error generating PDF: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate wall tile visualizations from JSON config.')
    parser.add_argument('config_file', help='Path to the JSON configuration file')
    parser.add_argument('--pdf', action='store_true', help='Generate a PDF of all visualizations')
    parser.add_argument('--mini', action='store_true', help='Use compression to minimize the PDF size')
    args = parser.parse_args()
    
    try:
        # Load the configuration file
        with open(args.config_file, 'r') as f:
            config = json.load(f)
        
        # Create the wall visualizations and get the list of generated images
        generated_images = create_wall_visualization(config)
        
        # If the pdf flag is set, generate a PDF with all the images
        if args.pdf and generated_images:
            # Create PDF filename based on the input JSON filename
            config_path = pathlib.Path(args.config_file)
            base_name = config_path.stem.replace('visualize-wall-', '')
            
            # Add '_mini' to the filename if --mini flag is used
            if args.mini:
                pdf_path = f"./out/visualize-wall-{base_name}_mini.pdf"
            else:
                pdf_path = f"./out/visualize-wall-{base_name}.pdf"
            
            # Pass the mini flag to the PDF generator
            pdf_header = config.get('title', 'Deltaware.in - Tiles Catalog - Whatsapp: 9940198130')
            generate_pdf(generated_images, pdf_path, compress=args.mini, title=pdf_header)
        
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file '{args.config_file}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
