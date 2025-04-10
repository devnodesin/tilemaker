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

def generate_pdf(image_paths, pdf_path, compress=False):
    """Generate a PDF containing all the generated images."""
    try:
        # Create the PDF
        c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        for img_path in image_paths:
            # Open the image
            img = Image.open(img_path)
            
            # If compression is enabled, reduce the image quality
            if compress:
                # Resize the image to reduce its dimensions (optional)
                # Here we're reducing by 30%
                new_size = (int(img.width * 0.7), int(img.height * 0.7))
                img = img.resize(new_size, Image.LANCZOS)
                
                # Save to a temporary file with compression
                temp_path = f"{img_path}_compressed.jpg"
                img.save(temp_path, "JPEG", quality=25)
                img = Image.open(temp_path)
                img_path = temp_path  # Use the compressed image
            
            # Resize the image to fit the PDF page while maintaining aspect ratio
            img_width, img_height = img.size
            img_ratio = img_width / img_height
            page_ratio = width / height
            
            if img_ratio > page_ratio:
                # Image is wider than the page (relative to height)
                new_width = width - 40  # 20px margin on each side
                new_height = new_width / img_ratio
            else:
                # Image is taller than the page (relative to width)
                new_height = height - 40  # 20px margin on top and bottom
                new_width = new_height * img_ratio
            
            # Center the image on the page
            x = (width - new_width) / 2
            y = (height - new_height) / 2
            
            # Add the image to the PDF
            c.drawImage(ImageReader(img), x, y, width=new_width, height=new_height)
            
            # Add a new page for the next image (if there is one)
            if img_path != image_paths[-1]:
                c.showPage()
            
            # Clean up temporary file if compression was used
            if compress and img_path.endswith("_compressed.jpg"):
                try:
                    os.remove(img_path)
                except:
                    pass
                
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
            generate_pdf(generated_images, pdf_path, compress=args.mini)
        
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file '{args.config_file}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
