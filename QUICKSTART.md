# Quick Start Guide

## Running the Application

### Step 1: Install Dependencies

```bash
pip install gradio Pillow numpy
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### Step 2: Run the Application

```bash
python app.py
```

Or use the startup script:

```bash
./run.sh
```

### Step 3: Open in Browser

The application will automatically open at:
```
http://localhost:7860
```

## Using the Application

### 1. **Select a Document**
   - Use the dropdown menu at the top to choose a PDF document
   - Available documents are automatically detected from `data/xml/*.json`

### 2. **Navigate Pages**
   - Use the page slider to move between pages
   - Current page number is shown on the slider

### 3. **View Bounding Boxes**
   - Left panel shows the PDF page with colored bounding boxes
   - Different colors represent different element types:
     - 🟥 Red: Headings (H1)
     - 🟧 Orange: Subheadings (H2, H3)
     - 🟦 Blue: Paragraphs (P)
     - 🟩 Green: Figures
     - 🟪 Magenta: Tables
     - 🟨 Yellow: Other elements

### 4. **Inspect Elements**
   - **Click on any bounding box** in the left panel
   - The corresponding JSON metadata will be highlighted in the right panel
   - The bounding box will be highlighted with a thicker border and semi-transparent fill

### 5. **View JSON Metadata**
   - Right panel shows all elements on the current page
   - Each element includes:
     - Element type and ID
     - Bounding box coordinates
     - Text content (if applicable)
     - Font information
     - Additional attributes

## Troubleshooting

### Issue: "No documents available"
**Solution:** Make sure your data is in the correct structure:
```
data/
├── png/              # Page images: {name}_page_{num:03d}.png
└── xml/              # JSON files: {name}.json
```

### Issue: "Image not found"
**Solution:** Verify that:
- PNG files exist in `data/png/`
- File names match the pattern: `{document_name}_page_{page_number:03d}.png`
- Example: `nvidia-a100-datasheet_page_001.png` for page 1

### Issue: "Bounding boxes misaligned"
**Solution:** The app now automatically reads exact page dimensions from the JSON metadata. If alignment is still off:
- Verify the `pages` array exists in your JSON with `width` and `height` fields
- Ensure images are rendered at consistent DPI with the PDF

### Issue: "Select Document dropdown not working"
**Solution:** This has been fixed in the latest version. Make sure you're running the updated `app.py`.

### Issue: Port 7860 already in use
**Solution:** Kill the existing process or change the port in `app.py`:
```python
app.launch(server_port=8080)  # Change to your preferred port
```

## Example Documents

The repository includes sample NVIDIA GPU datasheets:

| Document | Pages | File Size |
|----------|-------|-----------|
| A100 | 3 | ~200 elements |
| H100 | 3 | ~150 elements |
| H200 | 4 | ~180 elements |
| B200/B300 | 31 | ~1400 elements |
| GB200/GB300 | 7 | ~350 elements |
| GH200 | 4 | ~200 elements |

## Features

- ✅ Interactive bounding box visualization
- ✅ Click-to-highlight functionality
- ✅ JSON metadata viewer
- ✅ Multi-page navigation
- ✅ Color-coded element types
- ✅ Accurate coordinate transformation
- ✅ Responsive layout

## Performance Tips

- For documents with many elements (>500), initial page load may take 1-2 seconds
- Images are loaded and rendered on-demand for each page
- JSON parsing is cached after first load

## Next Steps

- Explore different documents using the dropdown
- Click on various elements to see their structure
- Compare how different element types (headings, paragraphs, tables) are structured
- Use this tool to debug PDF extraction results

## Need Help?

Check the main [README.md](README.md) for more detailed documentation and architecture information.

