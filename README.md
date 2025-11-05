# DC Visualizer - Document Structure Viewer

A Gradio-based web application for visualizing PDF document structure with interactive bounding boxes, similar to [Adobe's DC Visualizer](https://acrobatservices.adobe.com/dc-visualizer-app/index.html).

## Features

- 📄 **Document Selection**: Browse and load pre-processed PDF documents
- 🖼️ **Interactive Bounding Boxes**: View document elements overlaid on page images
- 📋 **JSON Metadata Display**: See detailed information about each element
- 🎯 **Click to Highlight**: Click on bounding boxes to view their corresponding JSON data
- 🎨 **Color-Coded Elements**: Different colors for different element types (headings, paragraphs, figures, tables, etc.)
- 📖 **Page Navigation**: Easy navigation through multi-page documents

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd dc-visualizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

Start the Gradio web interface:

```bash
python app.py
```

The application will launch on `http://localhost:7860` by default.

### Using the Interface

1. **Select a Document**: Choose a document from the dropdown menu
2. **Navigate Pages**: Use the page slider to move through the document
3. **Inspect Elements**: Click on any bounding box on the page image to see its JSON metadata highlighted in the right panel
4. **Understand Structure**: Different colors represent different element types:
   - 🟥 **Red**: Main Headings (H1)
   - 🟧 **Orange**: Subheadings (H2, H3)
   - 🟦 **Blue**: Paragraphs (P)
   - 🟩 **Green**: Figures
   - 🟪 **Magenta**: Tables
   - 🟨 **Yellow**: Other elements

## Data Structure

The application expects the following directory structure:

```
data/
├── pdf/              # Original PDF files
├── png/              # Extracted page images (named: {doc_name}_page_{num:03d}.png)
└── xml/              # JSON metadata files (named: {doc_name}.json)
```

### JSON Format

Each JSON file should contain:
- `version`: Metadata about the extraction process
- `extended_metadata`: Document-level information (page count, language, etc.)
- `elements`: Array of document elements, each with:
  - `Bounds`: `[x1, y1, x2, y2]` bounding box coordinates
  - `Page`: Page number (0-indexed)
  - `Path`: Structural path (e.g., `//Document/Sect/H1`)
  - `ObjectID`: Unique identifier
  - `Text`: Text content (for text elements)
  - Additional metadata (Font, Language, etc.)

### Coordinate System

- PDF coordinates use **bottom-left origin** (y increases upward)
- Image coordinates use **top-left origin** (y increases downward)
- The application handles coordinate transformation automatically

## Architecture

The application is organized into several key components:

### 1. Data Loading (`get_available_documents`, `load_document_data`)
Handles scanning and loading JSON metadata files

### 2. Element Processing (`get_element_type`, `get_elements_for_page`)
Extracts and filters elements based on page and type

### 3. Image Rendering (`draw_bounding_boxes`, `create_clickable_image`)
Draws bounding boxes on page images with proper coordinate transformation

### 4. JSON Display (`create_json_display`)
Formats and highlights JSON metadata in HTML

### 5. Event Handling (`handle_image_click`, `update_page_display`)
Manages user interactions and updates the interface

## Development

### Code Style

The code follows these principles:
- **Pedagogical**: Extensive comments explaining each function and its purpose
- **Modular**: Clear separation of concerns with focused functions
- **Type Hints**: Documented parameters and return types in docstrings
- **Readable**: Descriptive variable names and logical organization

### Extending the Application

To add new features:

1. **New Element Types**: Add entries to `COLOR_MAP` in the configuration section
2. **Different Visualizations**: Modify `draw_bounding_boxes` to change rendering
3. **Additional Metadata**: Update `create_json_display` to show more information
4. **Export Features**: Add functions to export highlighted elements or filtered data

## Example Documents

The repository includes sample NVIDIA GPU datasheets:
- A100 (3 pages)
- B200/B300 Blackwell (31 pages)
- GB200/GB300 Blackwell Ultra (7 pages)
- GH200 Grace Hopper (4 pages)
- H100 (3 pages)
- H200 (4 pages)

## Troubleshooting

### Images Not Loading
- Ensure PNG files exist in `data/png/` with correct naming format
- Check that page numbers in JSON match available images

### JSON Not Displaying
- Verify JSON files are in `data/xml/` directory
- Ensure JSON is valid and follows the expected structure

### Bounding Boxes Misaligned
- Check that images and JSON are from the same PDF
- Verify coordinate transformation logic for your specific PDF format

## License

See [LICENSE](LICENSE) file for details.

## Acknowledgments

Inspired by [Adobe DC Visualizer](https://acrobatservices.adobe.com/dc-visualizer-app/index.html)