"""
DC Visualizer - A Gradio app for visualizing PDF document structure with bounding boxes

This application displays PDF pages with interactive bounding boxes overlaid on the images,
alongside their corresponding JSON metadata. It's designed to help understand and debug
document structure extraction results.

Features:
- Upload PDF files or select from pre-loaded examples
- Navigate through pages with a slider
- Click on bounding boxes to see their JSON metadata
- Click on JSON elements to highlight their bounding boxes
- Color-coded bounding boxes by element type
"""

import gradio as gr
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ============================================================================
# Configuration and Constants
# ============================================================================

DATA_DIR = Path("data")
PNG_DIR = DATA_DIR / "png"
XML_DIR = DATA_DIR / "xml"
PDF_DIR = DATA_DIR / "pdf"

# Color mapping for different element types (Path attribute)
# These colors help distinguish different structural elements visually
COLOR_MAP = {
    "H1": "#FF0000",      # Red for main headings
    "H2": "#FF6B00",      # Orange for subheadings
    "H3": "#FFA500",      # Light orange
    "P": "#0000FF",       # Blue for paragraphs
    "Figure": "#00FF00",  # Green for figures
    "Table": "#FF00FF",   # Magenta for tables
    "L": "#00FFFF",       # Cyan for lists
    "default": "#FFFF00"  # Yellow for other elements
}

# Line width for bounding boxes
BBOX_LINE_WIDTH = 2
# Line width for highlighted (selected) bounding box
HIGHLIGHT_LINE_WIDTH = 4


# ============================================================================
# Helper Functions for Data Loading
# ============================================================================

def get_available_documents():
    """
    Scan the XML directory to find all available documents.
    
    Returns:
        list: List of document names (without .json extension)
    """
    if not XML_DIR.exists():
        return []
    
    json_files = sorted(XML_DIR.glob("*.json"))
    return [f.stem for f in json_files]


def load_document_data(document_name):
    """
    Load the JSON metadata for a given document.
    
    Args:
        document_name (str): Name of the document (without extension)
    
    Returns:
        dict: Parsed JSON data containing document elements and metadata
    """
    json_path = XML_DIR / f"{document_name}.json"
    
    if not json_path.exists():
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_page_image_path(document_name, page_num):
    """
    Get the file path for a specific page image.
    
    Args:
        document_name (str): Name of the document
        page_num (int): Page number (0-indexed)
    
    Returns:
        Path: Path to the page image file, or None if not found
    """
    # Page images are typically named: {document_name}_page_{num:03d}.png
    image_path = PNG_DIR / f"{document_name}_page_{page_num+1:03d}.png"
    
    if image_path.exists():
        return image_path
    return None


# ============================================================================
# Helper Functions for Element Processing
# ============================================================================

def get_element_type(element):
    """
    Extract the element type from the Path attribute.
    
    The Path typically looks like: //Document/Sect/H1 or //Document/P
    We extract the last component as the element type.
    
    Args:
        element (dict): Element from the JSON data
    
    Returns:
        str: Element type (e.g., "H1", "P", "Figure")
    """
    path = element.get("Path", "")
    if path:
        parts = path.split("/")
        return parts[-1] if parts else "unknown"
    return "unknown"


def get_element_color(element_type):
    """
    Get the color for a given element type.
    
    Args:
        element_type (str): Type of the element
    
    Returns:
        str: Hex color code
    """
    # Check if element type is in any of the predefined colors
    for key, color in COLOR_MAP.items():
        if key in element_type:
            return color
    return COLOR_MAP["default"]


def get_elements_for_page(data, page_num):
    """
    Filter elements for a specific page.
    
    Args:
        data (dict): Full document JSON data
        page_num (int): Page number (0-indexed)
    
    Returns:
        list: List of elements on the specified page
    """
    if not data or "elements" not in data:
        return []
    
    return [elem for elem in data["elements"] if elem.get("Page") == page_num]


# ============================================================================
# Image Rendering Functions
# ============================================================================

def get_pdf_page_size(data, page_num):
    """
    Get the exact PDF page size from the document metadata.
    
    This function reads the page dimensions from the 'pages' array in the JSON,
    which contains the actual MediaBox/CropBox dimensions from the PDF.
    Falls back to standard US Letter size (612 x 792 points) if not available.
    
    Args:
        data (dict): Full document JSON data
        page_num (int): Page number (0-indexed)
    
    Returns:
        tuple: (pdf_width, pdf_height) in points
    """
    # Try to get exact dimensions from pages array
    if data and 'pages' in data:
        pages = data['pages']
        if isinstance(pages, list) and page_num < len(pages):
            page_info = pages[page_num]
            if 'width' in page_info and 'height' in page_info:
                return page_info['width'], page_info['height']
    
    # Fall back to US Letter size (most common)
    return 612, 792


def draw_bounding_boxes(image_path, elements, data, page_num, highlighted_id=None, show_boxes=False):
    """
    Draw bounding boxes on the page image.
    
    This function:
    1. Loads the page image
    2. Gets exact PDF page dimensions from metadata
    3. Calculates scale factors between PDF and image coordinates
    4. Converts PDF coordinates to image coordinates with scaling
    5. Draws colored rectangles for each element (if show_boxes is True)
    6. Highlights the selected element with a thicker border
    
    Args:
        image_path (Path): Path to the page image
        elements (list): List of elements to draw
        data (dict): Full document JSON data (for page dimensions)
        page_num (int): Page number (0-indexed)
        highlighted_id (int): ObjectID of the element to highlight
        show_boxes (bool): Whether to draw bounding boxes (default: True)
    
    Returns:
        PIL.Image: Image with or without bounding boxes drawn
    """
    # Load the base image
    img = Image.open(image_path)
    
    # If bounding boxes are disabled, return the plain image
    if not show_boxes:
        return img
    
    draw = ImageDraw.Draw(img)
    
    # Get image dimensions
    img_width, img_height = img.size
    
    # Get exact PDF page size from metadata
    pdf_width, pdf_height = get_pdf_page_size(data, page_num)
    
    # Calculate scale factors
    # The PNG image is rendered at higher resolution than the PDF points
    scale_x = img_width / pdf_width
    scale_y = img_height / pdf_height
    
    # PDF coordinates have origin at bottom-left, y increases upward
    # Image coordinates have origin at top-left, y increases downward
    
    for element in elements:
        bounds = element.get("Bounds")
        if not bounds or len(bounds) != 4:
            continue
        
        # Extract PDF coordinates: [x1, y1, x2, y2]
        # In PDF: y1 is bottom, y2 is top
        pdf_x1, pdf_y1, pdf_x2, pdf_y2 = bounds
        
        # Scale coordinates to match image resolution
        scaled_x1 = pdf_x1 * scale_x
        scaled_x2 = pdf_x2 * scale_x
        scaled_y1 = pdf_y1 * scale_y
        scaled_y2 = pdf_y2 * scale_y
        
        # Flip Y-axis: image_y = image_height - pdf_y
        img_y1 = img_height - scaled_y2  # Top in image (was top in PDF)
        img_y2 = img_height - scaled_y1  # Bottom in image (was bottom in PDF)
        
        # Create rectangle coordinates for drawing
        rect = [scaled_x1, img_y1, scaled_x2, img_y2]
        
        # Determine if this element should be highlighted
        is_highlighted = (highlighted_id is not None and 
                         element.get("ObjectID") == highlighted_id)
        
        # Get color based on element type
        element_type = get_element_type(element)
        color = get_element_color(element_type)
        
        # Draw the bounding box
        line_width = HIGHLIGHT_LINE_WIDTH if is_highlighted else BBOX_LINE_WIDTH
        draw.rectangle(rect, outline=color, width=line_width)
        
        # For highlighted elements, also draw a semi-transparent fill
        if is_highlighted:
            # Create a semi-transparent overlay
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            # Convert hex color to RGB with alpha
            rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            overlay_draw.rectangle(rect, fill=rgb + (50,))  # 50 = ~20% opacity
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            img = img.convert('RGB')
            draw = ImageDraw.Draw(img)
    
    return img


def create_clickable_image(image_path, elements, data, page_num):
    """
    Create an image with clickable regions for each bounding box.
    
    This function prepares the image and metadata needed for making
    the bounding boxes interactive in Gradio.
    
    Args:
        image_path (Path): Path to the page image
        elements (list): List of elements on the page
        data (dict): Full document JSON data (for page dimensions)
        page_num (int): Page number (0-indexed)
    
    Returns:
        tuple: (image, elements) for storing state
    """
    img = draw_bounding_boxes(image_path, elements, data, page_num)
    return img, elements


# ============================================================================
# JSON Display Functions
# ============================================================================

def format_element_json(element, is_highlighted=False):
    """
    Format a single element as pretty-printed JSON with optional highlighting.
    
    Args:
        element (dict): Element to format
        is_highlighted (bool): Whether to highlight this element
    
    Returns:
        str: Formatted JSON string
    """
    json_str = json.dumps(element, indent=2)
    
    # If highlighted, wrap in HTML for styling
    if is_highlighted:
        return f'<div style="background-color: #ffffcc; padding: 10px; border: 2px solid #ff0000; border-radius: 5px; margin: 5px 0;">{json_str}</div>'
    
    return json_str


def create_json_display(elements, highlighted_id=None):
    """
    Create a formatted JSON display for all elements on the page.
    
    Args:
        elements (list): List of elements to display
        highlighted_id (int): ObjectID of the element to highlight
    
    Returns:
        str: HTML-formatted string with all elements wrapped in a scrollable container
    """
    if not elements:
        return "<div style='padding: 20px; text-align: center; color: #666; border: 1px solid #ddd; border-radius: 5px;'>No elements on this page</div>"
    
    # Create a list of formatted elements
    output = []
    
    for i, element in enumerate(elements):
        is_highlighted = (highlighted_id is not None and 
                         element.get("ObjectID") == highlighted_id)
        
        # Add element header with index and type
        element_type = get_element_type(element)
        object_id = element.get("ObjectID", "unknown")
        
        header_color = "#ff0000" if is_highlighted else "#333333"
        header = f'<h4 style="color: {header_color}; margin: 0 0 10px 0;">Element {i+1} - Type: {element_type} (ID: {object_id})</h4>'
        
        # Format the element JSON
        json_str = json.dumps(element, indent=2)
        
        # Wrap in a styled div
        bg_color = "#ffffcc" if is_highlighted else "#f5f5f5"
        border = "2px solid #ff0000" if is_highlighted else "1px solid #ddd"
        
        # Add an ID to the highlighted element for auto-scrolling
        # Add scroll-margin-top to ensure the element is centered when scrolled into view
        elem_id = f'id="element-{object_id}"' if is_highlighted else ''
        scroll_margin = 'scroll-margin-top: 100px;' if is_highlighted else ''
        
        elem_html = f'''
        <div {elem_id} style="background-color: {bg_color}; padding: 10px; border: {border}; 
                    border-radius: 5px; margin: 10px 0; font-family: monospace; white-space: pre-wrap; {scroll_margin}">
            {header}
            <pre style="margin: 5px 0; overflow-x: auto; font-size: 12px;">{json_str}</pre>
        </div>
        '''
        
        output.append(elem_html)
    
    # Wrap everything in a scrollable container with unique ID
    content = "\n".join(output)
    container_id = "json-container"
    
    # Add CSS styles for smooth scrolling
    css_styles = """
    <style>
        #json-container {
            scroll-behavior: smooth;
        }
        #json-container:focus-within {
            outline: none;
        }
    </style>
    """
    
    # Add JavaScript to auto-scroll to highlighted element
    # Using multiple approaches for maximum compatibility
    scroll_script = ""
    if highlighted_id is not None:
        # Add an anchor at the top to enable CSS :target scrolling as fallback
        anchor = f'<a id="scroll-to-{highlighted_id}"></a>'
        
        scroll_script = f'''
        <script>
        (function() {{
            // Wait for DOM to be ready
            setTimeout(function() {{
                var container = document.getElementById('{container_id}');
                var elem = document.getElementById('element-{highlighted_id}');
                
                if (container && elem) {{
                    // Calculate position to center the element in the container
                    var elemTop = elem.offsetTop;
                    var containerHeight = container.clientHeight;
                    var elemHeight = elem.clientHeight;
                    
                    // Scroll to center the element
                    var scrollTo = elemTop - (containerHeight / 2) + (elemHeight / 2);
                    
                    // Smooth scroll to the calculated position
                    container.scrollTo({{
                        top: Math.max(0, scrollTo),
                        behavior: 'smooth'
                    }});
                    
                    // Fallback: use scrollIntoView if scrollTo doesn't work
                    setTimeout(function() {{
                        elem.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'nearest' }});
                    }}, 50);
                }}
            }}, 200);
        }})();
        </script>
        '''
    else:
        anchor = ""
    
    return f'{css_styles}<div id="{container_id}" style="height: 1000px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">{anchor}{content}</div>{scroll_script}'


# ============================================================================
# Main Application Logic
# ============================================================================

def load_document(document_name):
    """
    Load a document and initialize the display with the first page.
    
    Args:
        document_name (str): Name of the document to load
    
    Returns:
        tuple: (image, json_html, page_slider, data, current_page)
    """
    # Load the document data
    data = load_document_data(document_name)
    
    if not data:
        return None, "Error: Could not load document", gr.update(), None, 0
    
    # Get page count
    page_count = data.get("extended_metadata", {}).get("page_count", 0)
    
    if page_count == 0:
        return None, "Error: No pages found", gr.update(), data, 0
    
    # Load first page
    page_num = 0
    return update_page_display(document_name, data, page_num)


def update_page_display(document_name, data, page_num, highlighted_id=None, show_boxes=False):
    """
    Update the display for a specific page.
    
    Args:
        document_name (str): Name of the current document
        data (dict): Full document JSON data
        page_num (int): Page number to display (0-indexed)
        highlighted_id (int): ObjectID to highlight
        show_boxes (bool): Whether to show bounding boxes (default: True)
    
    Returns:
        tuple: (image, json_html, page_slider_update, data, page_num)
    """
    if not data:
        return None, "No document loaded", gr.update(), None, 0
    
    # Get elements for this page
    elements = get_elements_for_page(data, page_num)
    
    # Get the page image
    image_path = get_page_image_path(document_name, page_num)
    
    if not image_path:
        return None, f"Error: Image not found for page {page_num + 1}", gr.update(), data, page_num
    
    # Draw the image with or without bounding boxes
    img = draw_bounding_boxes(image_path, elements, data, page_num, highlighted_id, show_boxes)
    
    # Create JSON display
    json_html = create_json_display(elements, highlighted_id)
    
    # Update page slider
    page_count = data.get("extended_metadata", {}).get("page_count", 1)
    slider_update = gr.update(maximum=page_count, value=page_num + 1)
    
    return img, json_html, slider_update, data, page_num


def handle_image_click(document_name, data, page_num, show_boxes, evt: gr.SelectData):
    """
    Handle clicks on the image to select bounding boxes.
    
    When a user clicks on the image, this function finds the element
    at that location and highlights it.
    
    Args:
        document_name (str): Name of the current document
        data (dict): Full document JSON data
        page_num (int): Current page number
        show_boxes (bool): Whether bounding boxes are visible
        evt (gr.SelectData): Gradio event data containing click coordinates
    
    Returns:
        tuple: Updated display with highlighted element
    """
    if not data:
        return None, "No document loaded", gr.update(), data, page_num
    
    # Get click coordinates (in image space)
    click_x, click_y = evt.index[0], evt.index[1]
    
    # Get elements for this page
    elements = get_elements_for_page(data, page_num)
    
    # Get image dimensions and calculate scale factors
    image_path = get_page_image_path(document_name, page_num)
    if not image_path:
        return None, "Error: Image not found", gr.update(), data, page_num
    
    img = Image.open(image_path)
    img_width, img_height = img.size
    
    # Get exact PDF page size from metadata and calculate scale factors
    pdf_width, pdf_height = get_pdf_page_size(data, page_num)
    scale_x = img_width / pdf_width
    scale_y = img_height / pdf_height
    
    # Find the element at the clicked location
    clicked_element = None
    for element in elements:
        bounds = element.get("Bounds")
        if not bounds or len(bounds) != 4:
            continue
        
        # Get PDF coordinates
        pdf_x1, pdf_y1, pdf_x2, pdf_y2 = bounds
        
        # Scale to image coordinates
        scaled_x1 = pdf_x1 * scale_x
        scaled_x2 = pdf_x2 * scale_x
        scaled_y1 = pdf_y1 * scale_y
        scaled_y2 = pdf_y2 * scale_y
        
        # Flip Y-axis to image coordinates
        img_y1 = img_height - scaled_y2
        img_y2 = img_height - scaled_y1
        
        # Check if click is within this bounding box
        if scaled_x1 <= click_x <= scaled_x2 and img_y1 <= click_y <= img_y2:
            clicked_element = element
            break
    
    if clicked_element:
        highlighted_id = clicked_element.get("ObjectID")
        return update_page_display(document_name, data, page_num, highlighted_id, show_boxes)
    
    # No element clicked, just refresh without highlight
    return update_page_display(document_name, data, page_num, None, show_boxes)


# ============================================================================
# Gradio Interface
# ============================================================================

def create_interface():
    """
    Create and configure the Gradio interface.
    
    Returns:
        gr.Blocks: Configured Gradio interface
    """
    # Get available documents
    available_docs = get_available_documents()
    
    with gr.Blocks(title="DC Visualizer - Document Structure Viewer") as app:
        # Header
        gr.Markdown("""
        # 📄 DC Visualizer - Dynamic Content Viewer
        
        This tool visualizes PDF document structure by displaying pages with bounding boxes
        overlaid on extracted elements. Each bounding box corresponds to a structural element
        (heading, paragraph, figure, etc.) in the document.
        
        **How to use:**
        1. Select a document from the dropdown
        2. Use the page slider to navigate through pages
        3. Click on bounding boxes to see their JSON metadata
        4. Different colors represent different element types
        """)
        
        # State variables to store current document data
        doc_data = gr.State(None)
        current_doc = gr.State("")
        current_page = gr.State(0)
        show_bbox_state = gr.State(False)  # Global state for bounding box visibility (hidden by default)
        
        # Document selection and controls
        with gr.Row():
            with gr.Column(scale=2):
                # Add empty option at the beginning
                doc_choices = [""] + available_docs
                doc_dropdown = gr.Dropdown(
                    choices=doc_choices,
                    label="Select Document",
                    value="",  # Start with empty option selected
                    interactive=True
                )
            with gr.Column(scale=1):
                page_slider = gr.Slider(
                    minimum=1,
                    maximum=1,
                    step=1,
                    value=1,
                    label="Page Number",
                    interactive=True
                )
            with gr.Column(scale=1):
                toggle_bbox_btn = gr.Button(
                    value="🔳 Show Bounding Boxes",
                    variant="secondary",
                    size="sm"
                )
            with gr.Column(scale=2):
                gr.Markdown("""
                **Legend:** 🟥 H1 | 🟧 H2/H3 | 🟦 Paragraphs | 🟩 Figures | 🟪 Tables | 🟨 Other
                """, elem_id="legend-compact")
        
        # Main content area - 50/50 split with aligned frames
        with gr.Row(equal_height=True):
            # Left panel: Image with bounding boxes (50% width)
            with gr.Column(scale=1):
                gr.Markdown("### 📷 Page View (Click on bounding boxes)", elem_classes="panel-header")
                image_display = gr.Image(
                    label="",
                    show_label=False,
                    interactive=False,
                    type="pil",
                    value=None,  # Start with no image
                    height=1000,  # Fixed height
                    elem_classes="aligned-component"
                )
            
            # Right panel: JSON data (50% width)
            with gr.Column(scale=1):
                gr.Markdown("### 📋 JSON Metadata (Click boxes to highlight)", elem_classes="panel-header")
                json_display = gr.HTML(
                    label="",
                    show_label=False,
                    value="<div style='padding: 20px; text-align: center; color: #666; border: 1px solid #ddd; border-radius: 5px;'><p style='margin-top: 100px; font-size: 16px;'>👆 Select a document from the dropdown above to begin</p><p style='font-size: 14px; color: #999;'>Click on any bounding box to view its JSON metadata</p></div>",
                    elem_classes="aligned-component"
                )
        
        # Custom CSS to ensure perfect alignment
        gr.HTML("""
        <style>
        .panel-header {
            margin-bottom: 0 !important;
            padding-bottom: 0.5em !important;
        }
        .aligned-component {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        /* Force same vertical alignment for both components */
        .image-container, .html-container {
            align-self: flex-start !important;
        }
        /* Remove all padding/margin from Gradio component wrappers */
        .image-container > div,
        .html-container > div {
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Target the actual content wrappers */
        .image-container .image-frame,
        .html-container > div > div {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        </style>
        """)
        
        # Event handlers
        
        # When a document is selected, load it
        def on_document_change(doc, show_boxes):
            """Handle document selection change"""
            if not doc or doc == "":
                # No document selected or empty option - return empty state (no scrollbar)
                empty_message = "<div style='padding: 20px; text-align: center; color: #666; border: 1px solid #ddd; border-radius: 5px;'><p style='margin-top: 100px; font-size: 16px;'>👆 Select a document from the dropdown above to begin</p><p style='font-size: 14px; color: #999;'>Click on any bounding box to view its JSON metadata</p></div>"
                return "", None, empty_message, gr.update(maximum=1, value=1), None, 0
            
            # Load the selected document (respecting current bbox state)
            data = load_document_data(doc)
            if not data:
                return doc, None, "Error: Could not load document", gr.update(), None, 0
            
            # Load first page with current bbox state
            img, json_html, slider_update, data_out, page = update_page_display(doc, data, 0, None, show_boxes)
            return doc, img, json_html, slider_update, data_out, page
        
        doc_dropdown.change(
            fn=on_document_change,
            inputs=[doc_dropdown, show_bbox_state],
            outputs=[current_doc, image_display, json_display, page_slider, doc_data, current_page]
        )
        
        # When page slider changes
        def on_page_change(doc, data, page, show_boxes):
            """Handle page slider change"""
            # Convert from 1-indexed slider to 0-indexed page number
            return update_page_display(doc, data, int(page) - 1, None, show_boxes)
        
        page_slider.change(
            fn=on_page_change,
            inputs=[current_doc, doc_data, page_slider, show_bbox_state],
            outputs=[image_display, json_display, page_slider, doc_data, current_page]
        )
        
        # When toggle button is clicked
        def on_bbox_toggle(doc, data, page, current_state):
            """Toggle bounding box visibility"""
            # Toggle the state
            new_state = not current_state
            
            # Update button text based on new state
            if new_state:
                btn_text = "🔲 Hide Bounding Boxes"
            else:
                btn_text = "🔳 Show Bounding Boxes"
            
            # If no document loaded, just update button and state
            if not doc or not data:
                return gr.update(value=btn_text), None, gr.update(), data, page, new_state
            
            # Update the display with new state
            img, json_html, slider, data_out, page_out = update_page_display(doc, data, page, None, new_state)
            return gr.update(value=btn_text), img, json_html, data_out, page_out, new_state
        
        toggle_bbox_btn.click(
            fn=on_bbox_toggle,
            inputs=[current_doc, doc_data, current_page, show_bbox_state],
            outputs=[toggle_bbox_btn, image_display, json_display, doc_data, current_page, show_bbox_state]
        )
        
        # When user clicks on the image
        image_display.select(
            fn=handle_image_click,
            inputs=[current_doc, doc_data, current_page, show_bbox_state],
            outputs=[image_display, json_display, page_slider, doc_data, current_page]
        )
        
        # Start with empty panels - no document loaded initially
        # User must select a document from the dropdown to begin
    
    return app


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Create and launch the Gradio interface
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,        # Default Gradio port
        share=False,             # Set to True to create a public link
        show_error=True          # Show detailed errors
    )

