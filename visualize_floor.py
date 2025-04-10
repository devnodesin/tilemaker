from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
import math
import numpy as np
import cv2
import argparse
import os
import json

IMAGE_OUTPUT_PATH = './out/visual/'

def parse_args():
    parser = argparse.ArgumentParser(description='Generate floor tile visualization')
    # Add all arguments first
    parser.add_argument('--json', type=str, help='JSON config file path')
    parser.add_argument('--rows', type=int, help='Number of rows, 20')
    parser.add_argument('--cols', type=int, help='Number of columns, 20')
    parser.add_argument('--title', type=str, help='Floor title')
    parser.add_argument('--rotate', action='store_true', help='Rotate alternate tiles in pattern')
    parser.add_argument('--padding', type=int, default=2, help='Padding between tiles (default: 2)')
    parser.add_argument('--in_file', type=str, help='Input tile image path')
    parser.add_argument('--out_file', type=str, help='Output file path (optional)')
    parser.add_argument('--pdf', action='store_true', help='Generate PDF output')
    
    # Parse arguments
    return parser.parse_args()

def apply_perspective(in_file: str, image: Image.Image, depth_factor: float = 2.0, saveFile: bool = False) -> Image.Image:
    """Apply perspective transform to make floor appear 3D and save result
    Args:
        in_file: Input filename for save path
        image: PIL Image to transform
        depth_factor: Controls perspective intensity (1.0-3.0)
    Returns:
        Transformed PIL Image
    """
    try:
        # Validate depth_factor
        depth_factor = max(1.0, min(3.0, depth_factor))
                
        # Convert PIL to OpenCV format
        img_cv = np.array(image)
        
        # Add padding to prevent cropping
        pad = 10
        img_padded = cv2.copyMakeBorder(img_cv, pad, pad, pad, pad, 
                                       cv2.BORDER_CONSTANT, value=[255, 255, 255])
        
        # Get dimensions
        height, width = img_padded.shape[:2]
        
        # Calculate offsets based on depth_factor
        inset = width * 0.15 * depth_factor   # Horizontal inset
        drop = height * 0.15 * depth_factor   # Vertical drop
        
        # Source points (original corners with padding)
        src_points = np.float32([
            [pad, pad],               # top-left
            [width-pad, pad],         # top-right
            [pad, height-pad],        # bottom-left
            [width-pad, height-pad]   # bottom-right
        ])
        
        # Destination points (transformed corners)
        dst_points = np.float32([
            [pad + inset, pad + drop],        # top-left moved down and right
            [width - pad - inset, pad + drop], # top-right moved down and left
            [pad, height-pad],                 # bottom-left unchanged
            [width-pad, height-pad]            # bottom-right unchanged
        ])
        
        # Calculate and apply transform
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        img_transformed = cv2.warpPerspective(img_padded, matrix, (width, height))
        
        # Convert back to PIL and crop padding
        result = Image.fromarray(img_transformed)
        result = result.crop((pad, pad, width-pad, height-pad))

        # Get dimensions after padding removal
        width, height = result.size

        # Calculate crop dimensions
        left_crop = 1100
        right_crop = 1100
        top_crop = 2200
        bottom_crop = 800

        # Validate crop values
        if left_crop + right_crop >= width or top_crop + bottom_crop >= height:
            print(f"Error: Crop values exceed image dimensions for file {in_file}. Skipping file.")
            return image
        
        # Print Image Size
        #print(f"Image size - Width: {width}, Height: {height}")
        # Print crop values
        #print(f"Crop values - Left: {left_crop}, Right: {right_crop}, Top: {top_crop}, Bottom: {bottom_crop}")

        # Apply all crops in one operation
        result = result.crop((
            left_crop,           # left
            top_crop,            # top
            width - right_crop,  # right
            height - bottom_crop # bottom
        ))

                
        # Save if filename provided
        if saveFile:
            out_file = f'{IMAGE_OUTPUT_PATH}{os.path.splitext(os.path.basename(in_file))[0]}_prep.jpg'
            result.save(out_file)
            print(f"Saving {out_file}")
            
        return result
        
    except Exception as e:
        print(f"Error applying perspective transform: {str(e)}")
        raise

def get_rotation(row: int, col: int) -> int:
    """Calculate rotation angle based on position.
    Top-left     Top-right
    (0,0) => 0°, (0,1) => -90°
    Bottom-left  Bottom-right
    (1,0) => 90, (1,1) => 180°
    Pattern repeats for larger grids
    """
    rotation_matrix = [
        [0, -90],  # row 0: [col 0, col 1]
        [90, 180]  # row 1: [col 0, col 1]
    ]
    return rotation_matrix[row % 2][col % 2]

def generate_floor(rows: int, cols: int, in_file: str, rotate: bool = False, padding: int = 0, saveFile: bool = False) -> Image.Image:
    
    try:
        # Load and resize tile image
        tile = Image.open(in_file)
        tile_size = 200  # pixels
        tile = tile.resize((tile_size, tile_size))
        
        # Create floor image without padding in dimensions
        floor = Image.new('RGB', (cols * tile_size, rows * tile_size), color='white')
        
        # Place tiles with rotation pattern and padding
        for row in range(rows):
            for col in range(cols):
                current_tile = tile.copy()
                if rotate:
                    angle = get_rotation(row, col)
                    current_tile = current_tile.rotate(angle)
                    
                # Calculate position - only add padding between tiles
                x = col * tile_size + (padding * col if col > 0 else 0)
                y = row * tile_size + (padding * row if row > 0 else 0)
                floor.paste(current_tile, (x, y))
        
        # Save result
        if saveFile:
            out_file = f'{IMAGE_OUTPUT_PATH}{os.path.splitext(os.path.basename(in_file))[0]}_top.jpg'
            print(f"Saving {out_file}")
            floor.save(out_file)
        return floor
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

def append_thumbnail(title: str, in_file: str, image: Image.Image, saveFile: bool = True) -> Image.Image:
    """Add thumbnail and title in white margin at bottom left of image
    Args:
        title: Text to display below thumbnail
        in_file: Path to thumbnail image
        image: Main image to append to
        saveFile: Whether to save result
    Returns:
        Modified image with thumbnail
    """
    try:
        # Constants
        THUMB_SIZE = (400, 400)
        PADDING = 20
        FONT_SIZE = 30  # Increased font size
        
        # Create thumbnail with margin
        thumb = Image.open(in_file)
        thumb.thumbnail(THUMB_SIZE)
        
        # Create thumbnail background with margin
        thumb_bg = Image.new('RGB', 
                           (THUMB_SIZE[0] + PADDING * 2, 
                            THUMB_SIZE[1] + PADDING * 2 + 35),  # Increased text space
                           (255, 255, 255))
        
        # Place thumbnail on white background
        thumb_bg.paste(thumb, (PADDING, PADDING))
        
        # Add title text with larger font
        draw = ImageDraw.Draw(thumb_bg)
        try:
            font = ImageFont.truetype("arial.ttf", FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        # Position text below thumbnail
        text_y = THUMB_SIZE[1] + PADDING + 5
        draw.text((PADDING, text_y), title, fill='black', font=font)
        
        # Create final image (same size as input)
        final = image.copy()
        
        # Place thumbnail at bottom left
        thumb_x = PADDING
        thumb_y = image.size[1] - thumb_bg.size[1] - PADDING
        final.paste(thumb_bg, (thumb_x, thumb_y))
        
        # Save if requested
        if saveFile:
            out_file = f'{IMAGE_OUTPUT_PATH}{os.path.splitext(os.path.basename(in_file))[0]}.jpg'
            final.save(out_file)
            print(f"Saved with thumbnail: {out_file}")
            
        return final
        
    except Exception as e:
        print(f"Error adding thumbnail: {str(e)}")
        raise

def make_pdf(files_list: list, pdf_path: str, title: str):
    try:
        print(f"Creating PDF...")
        # Constants
        PAGE_WIDTH, PAGE_HEIGHT = A4
        MARGIN = 15 * mm
        HEADER_OFFSET = 20 * mm
        FOOTER_OFFSET = 15 * mm
        IMAGE_MARGIN = 15 * mm
        HEADER_FONT_SIZE = 14
        PAGE_NUMBER_FONT_SIZE = 12
        IMAGES_PER_PAGE = 2
        LINE_OFFSET = 3 * mm
        
        # Calculate total pages and image size
        total_pages = math.ceil(len(files_list) / IMAGES_PER_PAGE)
        image_width = PAGE_WIDTH - (2 * MARGIN)
        image_height = (PAGE_HEIGHT - (2 * MARGIN) - HEADER_OFFSET - FOOTER_OFFSET - IMAGE_MARGIN) / IMAGES_PER_PAGE
        
        # Create PDF
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        c = canvas.Canvas(pdf_path, pagesize=A4)
        
        # Process images
        for i in range(0, len(files_list), IMAGES_PER_PAGE):
            # Add header
            c.setFont("Helvetica-Bold", HEADER_FONT_SIZE)
            c.drawString(MARGIN, PAGE_HEIGHT - MARGIN, title)
            
            # Add horizontal line below header
            c.setLineWidth(0.5)
            line_y = PAGE_HEIGHT - MARGIN - LINE_OFFSET
            c.line(MARGIN, line_y, PAGE_WIDTH - MARGIN, line_y)
            
            # Add images
            for j in range(IMAGES_PER_PAGE):
                if i + j < len(files_list):
                    img_path = files_list[i + j]
                    y_pos = PAGE_HEIGHT - MARGIN - HEADER_OFFSET - (image_height + IMAGE_MARGIN) * j
                    c.drawImage(img_path, 
                              MARGIN, 
                              y_pos - image_height,
                              width=image_width,
                              height=image_height,
                              preserveAspectRatio=True)
            
            # Add centered page number at bottom
            page_num = f"Page {(i // IMAGES_PER_PAGE) + 1} of {total_pages}"
            c.setFont("Helvetica", PAGE_NUMBER_FONT_SIZE)
            text_width = c.stringWidth(page_num, "Helvetica", PAGE_NUMBER_FONT_SIZE)
            x_position = (PAGE_WIDTH - text_width) / 2
            c.drawString(x_position, MARGIN, page_num)
            
            c.showPage()
        
        c.save()
        print(f"PDF Created: {pdf_path}")
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        raise

#####

def json_process(json_path: str, savePDF: bool = False) -> list:
    """Load JSON config and generate floor visualization
    Args:
        json_path: Path to JSON config file
    Returns:
        List of file paths for generated images
    """
    try:
        # Load JSON config
        with open(json_path) as f:
            config = json.load(f)
        
        # Extract common settings
        rows = config['rows']
        cols = config['cols']

        os.makedirs(IMAGE_OUTPUT_PATH, exist_ok=True)

        FileList = []
        
        # Process each page
        for page in config['pages']:
            # Build input file path
            in_file = page['file']
                       
            # Generate floor pattern
            floor = generate_floor(
                rows=rows,
                cols=cols,
                in_file=in_file,
                rotate=page['rotate'],
                padding=page['padding']
            )
            
            # Apply perspective transform
            floor = apply_perspective(in_file, floor, 2.5)

            # Append thumbnail with title
            floor = append_thumbnail(page['title'], in_file, floor)
            
            # Append to list for PDF generation
            FileList.append(f'{IMAGE_OUTPUT_PATH}{os.path.splitext(os.path.basename(in_file))[0]}.jpg')

        if savePDF:
            make_pdf(FileList, config['output_pdf'], config['title'])

        return FileList
            
            
    except Exception as e:
        print(f"Error processing JSON config: {str(e)}")
        raise

def main():
    args = parse_args()
    # Handle JSON case
    if args.json:
        print(f"Processing JSON Filename: {args.json}")
        files = json_process(args.json, args.pdf)
        

        
        
    else:
        # Validate required args for non-JSON case
        if not all([args.rows, args.cols, args.title, args.in_file]):
            print("Error: Missing required arguments")
        else:
            print("Direct processing\n\n")
            floor = generate_floor(args.rows, args.cols, args.in_file,  
                  args.rotate, args.out_file, args.padding)
            # Apply perspective transform
            floor = apply_perspective(args.in_file , floor, 2.5)

            # Append thumbnail with title
            floor = append_thumbnail(args.title, args.in_file, floor)


if __name__ == "__main__":
    main()