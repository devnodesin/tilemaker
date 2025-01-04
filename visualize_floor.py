from PIL import Image
import numpy as np
import cv2
import argparse
import os
import json

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
    
    # Parse arguments
    return parser.parse_args()

def apply_perspective(in_file: str, image: Image.Image, depth_factor: float = 2.0) -> Image.Image:
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
        
        # Get output filename
        if in_file:
            base_name = os.path.splitext(os.path.basename(in_file))[0]
            out_dir = './out/visual'
            os.makedirs(out_dir, exist_ok=True)
            prep_path = os.path.join(out_dir, f"{base_name}_prep.jpg")
        
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
        if in_file:
            result.save(prep_path)
            print(f"Perspective view saved to: {prep_path}")
            
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

def generate_floor(rows: int, cols: int, in_file: str, title: str, 
                  rotate: bool = False, out_file: str = None, padding: int = 0) -> Image.Image:
    """Generate floor tile visualization
    Args:
        rows: Number of tile rows
        cols: Number of tile columns
        in_file: Input tile image path
        title: Floor title
        rotate: Whether to rotate alternate tiles
        out_file: Optional output file path
        padding: Space between tiles (default: 0)
    Returns:
        PIL Image of generated floor
    """
    # ...existing code...
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
        
        # Determine output path
        if not out_file:
            os.makedirs('./out/visual', exist_ok=True)
            out_file = f'./out/visual/{os.path.splitext(os.path.basename(in_file))[0]}_top.jpg'
        
        # Save result
        floor.save(out_file)
        print(f"Floor visualization saved to: {out_file}")
        return floor
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

def json_process(json_path: str):
    """Load JSON config and generate floor visualization
    Args:
        json_path: Path to JSON config file
    """
    try:
        # Load JSON config
        with open(json_path) as f:
            config = json.load(f)
        
        # Extract common settings
        image_path = config['image_path']
        rows = config['rows']
        cols = config['cols']
        
        # Process each page
        for page in config['pages']:
            # Build input file path
            in_file = os.path.join(image_path, page['file'])
            
            # Generate output file path
            out_dir = './out/visual'
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, f"{page['title']}_floor.jpg")

            print(f"Processing page: {in_file}")
            
            # Generate floor pattern
            floor = generate_floor(
                rows=rows,
                cols=cols,
                in_file=in_file,
                title=page['title'],
                rotate=page['rotate'],
                out_file=None,  # Don't save intermediate
                padding=page['padding']
            )
            
            # Apply perspective transform
            floor = apply_perspective(in_file, floor, 2.5)
            
    except Exception as e:
        print(f"Error processing JSON config: {str(e)}")
        raise

def main():
    args = parse_args()
    # Handle JSON case
    if args.json:
        print(f"Filename: {args.json}")
        json_process(args.json)
    else:
        # Validate required args for non-JSON case
        if not all([args.rows, args.cols, args.title, args.in_file]):
            print("Error: Missing required arguments")
        else:
            print("Direct processing\n\n")
            floor = generate_floor(args.rows, args.cols, args.in_file, args.title, 
                  args.rotate, args.out_file, args.padding)
            # Apply perspective transform
            floor = apply_perspective(args.in_file , floor, 2.5)


if __name__ == "__main__":
    main()