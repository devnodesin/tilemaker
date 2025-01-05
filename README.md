# PDF Product Catalog Generator

A Python script that generates a PDF catalog from a directory of product images with titles and organized layout.

## Requirements

- Python 3.x
- Pillow (PIL)
- ReportLab

## Installation

Install required packages using pip:

```bash
pip install Pillow reportlab
```

## Usage

`simple_catalog.py` generates a PDF catalog from a directory of images. It automatically arranges images in a grid layout, adds page numbers, and creates a clean professional output. Images are resized and optimized for consistent display.

```bash
$ py simple_catalog.py --img ./images/mcl/parking/
Product catalog created: out/product_catalog.pdf
```

`make_catalog.py` creates PDF catalogs using a JSON configuration file. Features include:

- Customizable page layouts and margins
- Title and file name mapping
- Grid-based image arrangement
- Professional headers and page numbers

```bash
$ py  make_catalog.py --config catalog/parking-tiles.json
Catalog generated: out/parking-tiles.pdf
```

```bash
$ py visualize_floor.py --rows 20 --cols 20 --title "kitchen" --in_file ".\images\mcl\parking\14400.jpg" --rotate --padding=2
```

```bash
$ py .\visualize_floor.py --json .\catalog\visualize-parking.json

or 

$ py .\visualize_floor.py --json .\catalog\visualize-parking.json --pdf
```
