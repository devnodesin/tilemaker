# Tiles Layout Maker (`webapp/tile_layout_maker.html`)

This HTML file provides a web-based tool to estimate the number of tile boxes required for covering a specific area (like a wall or floor section) based on room dimensions and different tile variants arranged in rows. It allows users to visualize the layout with uploaded images and calculate the necessary materials.

## Features

- **Room Dimensions:** Input the length and height (referred to as width in the code, but likely means height in context of wall tiling) of the area in feet.
- **Location & Model:** Optional fields to specify the location (e.g., "Hall") and tile model (e.g., "1122").
- **Tile Variants:**
  - Add multiple rows, each representing a different tile variant or section.
  - Select predefined tile sizes (currently only "18x12" is configured in [`tilesData`](webapp/tile_layout_maker.html)).
  - Upload or drag-and-drop an image for each tile variant for visual representation in the output.
  - Assign a variant identifier (e.g., 'D' for Dark, 'L' for Light).
  - Specify the number of rows required for each variant (supports fractional rows like 0.25, 0.5, 0.75, 1.5, etc.).
- **Calculation:**
  - Calculates the square footage covered by each variant row based on room length and tile width.
  - Determines the number of boxes needed for each variant, rounding up to the nearest whole box.
  - Calculates the total square footage of the room and the total boxes needed for all variants.
- **Output:**
  - Displays a summary including location, model, room dimensions, and total square footage/boxes.
  - Shows each variant with its calculated details (boxes needed, square footage).
  - Visually represents the tile rows using the uploaded images, including fractional tiles clipped appropriately (`.img-quarter`, `.img-half`, `.img-three-quarters`).
- **Actions:**
  - **Print:** Prints only the calculated output area.
  - **Copy:** Copies the generated output HTML to the clipboard (uses modern Clipboard API with fallback).
- **Theme:** Includes a Light/Dark theme switcher using Bootstrap's theme attributes, saving the preference in `localStorage`.
- **Responsive Design:** Adapts layout for different screen sizes.

## How to Use

1. Open the [`webapp/tile_layout_maker.html`](webapp/tile_layout_maker.html) file in a web browser.
2. Enter the room's **Length** and **Height** in feet into the respective input fields.
3. Optionally, fill in the **Location** and **Model** fields.
4. In the **Variants** table:
   - The first row is added by default.
   - Select the **Tile Size** (only "18x12" available currently).
   - Click or drag/drop an image onto the **Image** drop zone.
   - Enter a short name for the **Variant** (e.g., "D").
   - Enter the number of **Rows** this variant occupies (e.g., `2`, `3.5`, `0.75`).
   - Use the **Add Row** button to add more variants as needed.
   - Use the trash icon <i class="bi bi-trash"></i> to remove rows (cannot remove the last row).
5. Click the **Calculate** button.
6. The results will appear in the output area on the right (or below on smaller screens).
7. Use the **Print** or **Copy** buttons above the output area as needed.

## Technical Details

- Frontend only: Uses HTML, CSS, and vanilla JavaScript.
- Styling: Leverages Bootstrap 5 for layout and components, with custom CSS for specific elements like the output area, image drop zones, and fractional image display.
- Image Handling: Uses the `FileReader` API to read and display local image files without uploading them to a server.
- Calculations: Performed entirely in client-side JavaScript within the [`calculateAndDisplayOutput`](webapp/tile_layout_maker.html) function.
- Interactivity: DOM manipulation for adding/removing rows, updating previews, and displaying results.
