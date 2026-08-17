# Kairos Image Converter

A modern, user-friendly desktop application for batch converting images between multiple formats with an elegant dark-themed interface.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)

## Features

- **Multiple Format Support**: Convert between JPEG, PNG, WEBP, BMP, TIFF, GIF, HEIC, and ICO formats
- **Batch Processing**: Convert multiple images at once with drag-and-drop support
- **Smart ICO Generation**: Automatically generates multi-resolution ICO files with standard sizes (16x16 to 256x256)
- **Quality Control**: Adjustable quality settings (0-100) for JPEG, WEBP, and HEIC formats
- **Image Resizing**: Optional width and height adjustments while maintaining aspect ratio
- **Custom Output Directory**: Choose where to save converted images or use source directory
- **Real-time Progress Tracking**: Monitor conversion progress with visual feedback per image
- **Error Handling**: Detailed error reporting for failed conversions with tooltips
- **Dark Theme UI**: Modern, eye-friendly interface with purple accent colors (#8b5cf6)
- **Drag & Drop**: Simply drag images into the application window (powered by tkinterdnd2)
- **File Preview**: View thumbnails and details of queued images in elegant cards
- **Cancellation Support**: Stop ongoing batch conversions at any time
- **Smart File Naming**: Automatic file renaming to prevent overwriting existing files

## Screenshots

The application features a clean, modern interface with:
- **Drop Zone**: Drag-and-drop area for easy file addition with click-to-browse support
- **Image Cards**: Individual cards showing thumbnails (80x80), file names, sizes, and dimensions
- **Progress Indicators**: Real-time progress bars with status (pending/converting/done/error)
- **Statistics Panel**: Live counters for converted and failed images
- **Control Panel**: Format selector, quality slider, dimension inputs, and output directory chooser
- **Action Buttons**: Convert All (with cancel support) and Clear All buttons

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

The project includes a PyInstaller spec file (`Image_Converter.spec`) for creating a standalone Windows executable:

### Prerequisites for Building
```bash
pip install pyinstaller
```

### Build Command
```bash
pyinstaller "Image_Converter.spec"
```

The executable will be created in the `dist/Image Converter` folder as `Image Converter.exe`. The spec file automatically includes:
- Application icons (kairos_icon.ico and kairos_icon.png)
- All required dependencies
- No console window (windowed mode)
- UPX compression for smaller executable size

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
- **Transparency Handling**: Automatic white background conversion for JPEG/HEIC when source has transparency
- **Aspect Ratio Preservation**: Resizing maintains original proportions using LANCZOS resampling
- **File Name Safety**: Automatic renaming with numeric suffixes to prevent overwriting existing files
- **Multi-threading**: Non-blocking UI during batch conversions using threading
- **Memory Efficient**: Releases file handles immediately after loading with `img.load()`
- **Smart Cropping**: Automatic transparent padding removal for ICO files
- **Center Positioning**: ICO images centered in square canvas with aspect ratio preserved

### Color Scheme
- Background: `#0a0a12` (Deep Dark Blue)
- Surface: `#14141f` (Dark Surface)
- Card: `#181826` (Card Background)
- Card Hover: `#1e1e30` (Card Hover State)
- Border: `#26263a` (Subtle Borders)
- Accent: `#8b5cf6` (Purple Primary)
- Accent Hover: `#a78bfa` (Purple Secondary)
- Success: `#22c55e` (Green)
- Error: `#f43f5e` (Red)
- Text: `#f1f5f9` (Primary Text)
- Subtext: `#8b8ca3` (Secondary Text)

## Architecture

The application is built with a clean, modular structure using Python's Tkinter and tkinterdnd2:

### Core Components

- **RoundedButton**: Custom Canvas-based button widget with:
  - Hover effects and state management (enabled/disabled)
  - Configurable colors and text
  - Click event handling
  
- **ImageCard**: Individual card component for each queued image featuring:
  - 80x80 thumbnail preview
  - File information (name, size, dimensions)
  - Progress bar with four states (pending, converting, done, error)
  - Remove button with hover effects
  - Error tooltip display
  
- **ImageConverterApp**: Main application class (TkinterDnD.Tk) managing:
  - UI layout with sidebar and main canvas
  - Drag-and-drop file handling
  - Conversion queue management
  - Threading for non-blocking batch conversions
  - Progress tracking and statistics updates
  
### Helper Functions

- `_crop_transparent_padding()`: Removes transparent padding from images using alpha channel bounding box
- `_fit_square()`: Resizes image to fit within a square canvas while maintaining aspect ratio
- `_save_ico()`: Manually generates ICO files with proper BITMAPINFOHEADER structure and BGRA data
- `_unique_path()`: Generates unique file paths with numeric suffixes to prevent overwrites
- `_load_logo_photo()`: Loads and processes the application icon for UI display

## Known Limitations

- **Platform**: Designed for Windows (uses Windows-style path handling and ctypes for app model ID)
- **ICO Format**: Limited to 256x256 maximum dimension per Windows ICO standard
- **No Undo**: No batch undo functionality for conversions
- **Progress Granularity**: Progress bar updates per-batch iteration, not per-file completion
- **HEIC Encoding**: HEIC output quality may vary based on pillow-heif encoder availability
- **Single Instance**: No multi-window support

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

If HEIC files still don't work, verify the pillow-heif opener is registered (it's automatic in the app code).

### Drag and drop not working
Verify `tkinterdnd2` is installed correctly:
```bash
pip install --upgrade tkinterdnd2
```

On some systems, you may need to install it from source or use a compatible version. The application requires version 0.3.0 or higher.

### Application icon not displaying
Ensure both `kairos_icon.ico` and `kairos_icon.png` are in the same directory as `app.py`. These files are required for proper UI rendering and taskbar display.

### Conversion fails silently
Check the error tooltip by hovering over failed image cards (red progress bar). Common issues include:
- Corrupted image files
- Insufficient disk space
- Invalid output directory permissions
- Unsupported image modes for target format

## Project Structure

```
Kairos Image converter/
├── app.py                    # Main application code (~750 lines)
├── requirements.txt          # Python dependencies
├── Image_Converter.spec      # PyInstaller build configuration
├── kairos_icon.ico          # Application icon (Windows)
├── kairos_icon.png          # Application icon (UI display)
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── build/                   # PyInstaller build artifacts (gitignored)
└── dist/                    # Compiled executable output (gitignored)
```

## Performance Notes

- **Conversion Speed**: Depends on image size, format complexity, and quality settings
- **Memory Usage**: Efficiently manages memory with immediate file handle release after loading
- **Threading**: Uses Python's threading module for non-blocking UI during batch operations
- **Thumbnail Generation**: Thumbnails are cached within ImageCard instances for smooth scrolling
- **ICO Generation**: Custom implementation bypasses Pillow's ICO writer for better multi-resolution support

## Future Enhancements

Potential features for future versions:
- Cross-platform support (macOS, Linux)
- Batch undo/redo functionality
- Image preview zoom and pan
- Watermark and text overlay options
- Advanced cropping and rotation tools
- Preset configurations for common use cases
- Command-line interface for scripting
- Multi-language support

## Contributing

Contributions are welcome! Here's how you can help:

1. **Report Bugs**: Open an issue with detailed reproduction steps
2. **Suggest Features**: Describe new features with use cases
3. **Submit Pull Requests**: Fork the repository and submit PRs with clear descriptions
4. **Improve Documentation**: Help make the README and code comments clearer

Please ensure your code follows the existing style and includes appropriate comments.

## License

This project is open source and available under the MIT License.

## Author

Developed for efficient batch image conversion with a focus on user experience and modern design principles. Built with Python, Tkinter, and Pillow.

## Version History

### Current (2026)
- Full-featured image converter with 8 format support
- Multi-resolution ICO generation with smart cropping
- HEIC/HEIF format support via pillow-heif
- Drag-and-drop interface with tkinterdnd2
- Real-time progress tracking per image
- Cancel conversion support
- Dark themed modern UI with purple accents
- Error tooltips and detailed feedback
- Smart file naming to prevent overwrites

---

**Note**: This application is designed primarily for Windows environments. Cross-platform compatibility may require adjustments to file path handling, icon loading, and UI elements. The application has been tested on Windows 10/11 with Python 3.7+.
