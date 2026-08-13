# Kairos Image Converter

A modern, user-friendly desktop application for batch converting images between multiple formats with an elegant dark-themed interface.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Multiple Format Support**: Convert between JPEG, PNG, WEBP, BMP, TIFF, GIF, HEIC, and ICO formats
- **Batch Processing**: Convert multiple images at once with drag-and-drop support
- **Smart ICO Generation**: Automatically generates multi-resolution ICO files with standard sizes (16x16 to 256x256)
- **Quality Control**: Adjustable quality settings for JPEG, WEBP, and HEIC formats
- **Image Resizing**: Optional width and height adjustments while maintaining aspect ratio
- **Custom Output Directory**: Choose where to save converted images
- **Real-time Progress Tracking**: Monitor conversion progress with visual feedback
- **Error Handling**: Detailed error reporting for failed conversions
- **Dark Theme UI**: Modern, eye-friendly interface with purple accent colors
- **Drag & Drop**: Simply drag images into the application window
- **File Preview**: View thumbnails and details of queued images

## Screenshots

The application features:
- Drop zone for easy file addition
- Individual image cards with thumbnails and file information
- Real-time conversion progress bars
- Statistics panel showing converted/failed counts
- Configurable output settings

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. Clone or download this repository:
```bash
git clone <repository-url>
cd "Kairos Image converter"
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

### Dependencies

- **Pillow** (>=10.0.0) - Image processing library
- **tkinterdnd2** (>=0.3.0) - Drag and drop support for Tkinter
- **pillow-heif** (>=0.18.0) - HEIC/HEIF format support

## Usage

### Running the Application

```bash
python app.py
```

### Basic Workflow

1. **Add Images**: 
   - Drag and drop image files into the application window, or
   - Click the drop zone to browse and select files

2. **Configure Settings**:
   - Select output format from the dropdown
   - (Optional) Adjust quality slider for JPEG/WEBP/HEIC
   - (Optional) Set custom width/height for resizing
   - (Optional) Choose a custom output directory

3. **Convert**:
   - Click "Convert All" to start batch conversion
   - Monitor progress in real-time
   - View statistics for completed and failed conversions

4. **Manage Queue**:
   - Click "×" on individual cards to remove them
   - Use "Clear All" to remove all images from the queue

### Special Features

#### ICO Conversion
When converting to ICO format:
- Automatically crops transparent padding
- Generates multiple resolutions (16, 32, 48, 64, 128, 256 pixels)
- Maintains aspect ratio with center positioning
- Perfect for creating application icons

#### HEIC Support
Full support for Apple's HEIC format:
- Read HEIC/HEIF files
- Convert to/from HEIC with quality control
- Automatic transparency handling

## Building Executable

The project includes a PyInstaller spec file for creating a standalone executable:

```bash
pyinstaller "K Vaults.spec"
```

The executable will be created in the `dist` folder.

## Technical Details

### Supported Input Formats
- JPEG/JPG
- PNG
- WEBP
- BMP
- TIFF
- GIF
- HEIC/HEIF
- ICO

### Supported Output Formats
- JPEG (with quality control)
- PNG
- WEBP (with quality control)
- BMP
- TIFF
- GIF
- HEIC (with quality control)
- ICO (multi-resolution)

### Image Processing Features
- **Transparency Handling**: Automatic background conversion for JPEG/HEIC when source has transparency
- **Aspect Ratio Preservation**: Resizing maintains original proportions
- **File Name Safety**: Automatic renaming to prevent overwriting existing files
- **Multi-threading**: Non-blocking UI during batch conversions
- **Memory Efficient**: Releases file handles after loading

### Color Scheme
- Background: `#0a0a12`
- Surface: `#14141f`
- Card: `#181826`
- Accent: `#8b5cf6` (Purple)
- Success: `#22c55e` (Green)
- Error: `#f43f5e` (Red)

## Architecture

The application is built with a clean, modular structure:

- **RoundedButton**: Custom Canvas-based button widget with hover effects
- **ImageCard**: Individual card component for each queued image
- **ImageConverterApp**: Main application class managing UI and conversion logic
- **Helper Functions**: 
  - `_crop_transparent_padding()`: Smart ICO preparation
  - `_fit_square()`: Aspect-ratio-preserving resize
  - `_save_ico()`: Manual ICO file generation with proper BMP headers
  - `_unique_path()`: Prevents file overwrites

## Known Limitations

- Windows-style path handling (designed for Windows)
- ICO format limited to 256x256 maximum dimension per standard
- No batch undo functionality
- Progress tracking is per-batch, not per-file during conversion

## Troubleshooting

### "Module not found" errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### HEIC files not working
Make sure `pillow-heif` is properly installed and up to date:
```bash
pip install --upgrade pillow-heif
```

### Drag and drop not working
Verify `tkinterdnd2` is installed correctly. On some systems, you may need to install it from source.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is open source and available under the MIT License.

## Author

Developed for efficient batch image conversion with a focus on user experience and modern design principles.

## Version History

- **Current**: Full-featured image converter with multi-format support
- Includes ICO multi-resolution generation
- HEIC format support
- Drag-and-drop interface
- Real-time progress tracking

---

**Note**: This application is designed for Windows environments. Cross-platform compatibility may require adjustments to file path handling and UI elements.
