import os
import json
import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pathlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
# Add these imports for embedding fonts
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_wall_visualization(config):
    """Create wall tile visualizations based on the provided configuration."""
    
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
        
        # Get random images if available
        random_image_paths = []
        if 'images_random' in page:
            random_image_paths = [os.path.join(page['path'], img) for img in page['images_random']]
        
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
            current_row_img_idx = 0  # Track the current image index for the row
            for row in range(rows):
                # Determine which image to use for this row
                if row < len(image_paths):
                    current_row_img_idx = row
                else:
                    # If we've used all images, restart from the first image
                    current_row_img_idx = row % len(image_paths)
                    
                img_path = image_paths[current_row_img_idx]
                
                for col in range(cols):
                    if random_image_paths:
                        # Pattern: original image at even positions, random at odd positions
                        if (row + col) % 2 == 0:
                            # Use the current row's main image
                            current_img_path = img_path
                        else:
                            # Use a random image from the random_image_paths
                            # Use a consistent seed for reproducibility but still get variety
                            np.random.seed((row + 1) * (col + 1) + np.random.randint(100))
                            current_img_path = np.random.choice(random_image_paths)
                    else:
                        # Without random images, just repeat the row's main image across all columns
                        current_img_path = img_path
                    
                    try:
                        img = Image.open(current_img_path)
                        x = col * (img_width + padding)
                        y = row * (img_height + padding)
                        wall_image.paste(img, (x, y))
                    except Exception as e:
                        print(f"Error processing image {current_img_path}: {e}")
            
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

def generate_pdf(image_paths, pdf_path, title='', cover_image_path=None, print_ready=False, page_count=None):
    """Generate a PDF containing all the generated images (2 per page)."""
    try:
        # Create the PDF with US Letter (8.5" x 11") size
        # 1 inch = 72 points, so 8.5" x 11" = 612 x 792 points
        letter_size = (612, 792)  # Width: 8.5", Height: 11" in points
        
        # Register and embed fonts if print_ready is enabled
        if print_ready:
            try:
                # Register common fonts for embedding
                helvetica_path = os.path.join(os.environ.get('WINDIR', ''), 'Fonts', 'arial.ttf')
                if os.path.exists(helvetica_path):
                    pdfmetrics.registerFont(TTFont('Helvetica', helvetica_path))
                    pdfmetrics.registerFont(TTFont('Helvetica-Bold', os.path.join(os.environ.get('WINDIR', ''), 'Fonts', 'arialbd.ttf')))
                print("Fonts embedded for print-ready output")
            except Exception as e:
                print(f"Warning: Could not embed fonts: {e}. Using default fonts.")
        
        # Create PDF with print-ready settings if needed
        c = canvas.Canvas(pdf_path, pagesize=letter_size)
        if print_ready:
            # Set PDF metadata for print-ready document
            c.setTitle(f"Print-Ready Tile Catalog - {title}")
            c.setSubject("Tile Catalog for Print")
            c.setAuthor("Deltaware.in")
            c.setCreator("TileMaker Visualization Tool")
            c.setKeywords("tiles, catalog, print")
        
        width, height = letter_size  # Use letter size dimensions
        
        # Calculate how many pages we'll need for images (2 images per page)
        has_cover = cover_image_path and os.path.exists(cover_image_path)
        actual_pages = (len(image_paths) + 1) // 2
        total_actual_pages = actual_pages + (1 if has_cover else 0)
        
        # If page_count is specified and greater than actual pages, we'll add empty pages
        total_pages_to_generate = max(total_actual_pages, page_count or 0)
        if page_count and page_count > total_actual_pages:
            print(f"Adding {page_count - total_actual_pages} empty pages to meet requested page count of {page_count}")
        
        # Calculate the final total pages for page numbering
        total_pages_with_cover = total_pages_to_generate 
        
        # Add cover page if provided
        if cover_image_path and os.path.exists(cover_image_path):
            try:
                cover_img = Image.open(cover_image_path)
                
                # Resize cover image to fit the page while maintaining aspect ratio
                cover_img_width, cover_img_height = cover_img.size
                img_ratio = cover_img_width / cover_img_height
                
                # Calculate dimensions to fill the page with margins
                margin = 10
                usable_width = width - (2 * margin)
                usable_height = height - (2 * margin)
                
                # Determine the best fit dimensions
                if img_ratio > usable_width / usable_height:  # Width-constrained
                    new_width = usable_width
                    new_height = new_width / img_ratio
                else:  # Height-constrained
                    new_height = usable_height
                    new_width = new_height * img_ratio
                
                # Center the cover image on the page
                x = margin + (usable_width - new_width) / 2
                y = margin + (usable_height - new_height) / 2
                
                c.drawImage(ImageReader(cover_img), x, y, width=new_width, height=new_height)
                c.showPage()  # Finish the cover page and start a new page
                
            except Exception as e:
                print(f"Error processing cover image: {e}")
        
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
            # Calculate page number considering the cover page
            page_num = (i // 2) + 1
            page_num_with_cover = page_num + (1 if cover_image_path and os.path.exists(cover_image_path) else 0)
            
            # Add header with the page title
            c.setFont("Helvetica-Bold", 12)
            header_text = f"{title}"
            text_width = c.stringWidth(header_text, "Helvetica-Bold", 12)
            c.drawString(margin + (usable_width - text_width) / 2, height - margin - 15, header_text)
            
            # Add the first image
            img1_path = image_paths[i]
            img1 = Image.open(img1_path)
            
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
            
            # Add second image if available
            if i + 1 < len(image_paths):
                img2_path = image_paths[i + 1]
                img2 = Image.open(img2_path)
                
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
            
            # Add page number at bottom center
            c.setFont("Helvetica", 10)
            page_text = f"Page {page_num_with_cover} of {total_pages_with_cover}"
            text_width = c.stringWidth(page_text, "Helvetica", 10)
            c.drawString((width - text_width) / 2, margin + 5, page_text)
            
            # Add a new page if there are more images to come
            if i + 2 < len(image_paths):
                c.showPage()
        
        # Add empty pages if needed to meet the specified page count
        for j in range(total_actual_pages, total_pages_to_generate):
            # Start a new empty page
            c.showPage()
            
            # Add header with the page title (on empty pages too)
            c.setFont("Helvetica-Bold", 12)
            header_text = f"{title}"
            text_width = c.stringWidth(header_text, "Helvetica-Bold", 12)
            c.drawString(margin + (usable_width - text_width) / 2, height - margin - 15, header_text)
            
            # Add page number at bottom center for empty pages too
            c.setFont("Helvetica", 10)
            empty_page_num = j + 1
            page_text = f"Page {empty_page_num} of {total_pages_with_cover}"
            text_width = c.stringWidth(page_text, "Helvetica", 10)
            c.drawString((width - text_width) / 2, margin + 5, page_text)
        
        # Save the PDF
        c.save()
        print(f"Created PDF: {pdf_path} with {total_pages_to_generate} total pages")
        
    except Exception as e:
        print(f"Error generating PDF: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate wall tile visualizations from JSON config.')
    parser.add_argument('config_file', help='Path to the JSON configuration file')
    parser.add_argument('--pdf', action='store_true', help='Generate a PDF of all visualizations')
    parser.add_argument('--cover', help='Path to the cover image to use as the first page of the PDF')
    parser.add_argument('--print', nargs='?', const=None, type=int, metavar='PAGE_COUNT',
                        help='Generate a print-ready PDF with embedded fonts. Optional: specify total page count.')
    args = parser.parse_args()
    
    try:
        # Load the configuration file
        with open(args.config_file, 'r') as f:
            config = json.load(f)
        
        # Create the wall visualizations and get the list of generated images
        generated_images = create_wall_visualization(config)
        
        # If the pdf flag is set, generate a PDF with all the images
        if (args.pdf or args.print is not None) and generated_images:
            # Create PDF filename based on the input JSON filename
            config_path = pathlib.Path(args.config_file)
            base_name = config_path.stem.replace('visualize-wall-', '')
            pdf_path = f"./out/visualize-wall-{base_name}.pdf"
            
            # If print-ready option is set, modify the filename
            if args.print is not None:
                # Include page count in filename if specified
                if args.print:
                    pdf_path = f"./out/visualize-wall-{base_name}-print-{args.print}.pdf"
                else:
                    pdf_path = f"./out/visualize-wall-{base_name}-print.pdf"
            
            # Pass the cover image path to the PDF generator
            pdf_header = config.get('title', 'Deltaware.in - Tiles Catalog - Whatsapp: 9940198130')
            cover_image_path = args.cover
            
            # Generate PDF with the optional page count
            generate_pdf(generated_images, pdf_path, title=pdf_header, 
                        cover_image_path=cover_image_path, print_ready=(args.print is not None), 
                        page_count=args.print)
            
            if args.print is not None:
                print_message = f"Generated print-ready PDF with embedded fonts: {pdf_path}"
                if args.print:
                    print_message += f" (with {args.print} total pages)"
                print(print_message)
        
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file '{args.config_file}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
