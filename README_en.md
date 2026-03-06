# ✂️ Markorez

A smart tool for automatic searching and cropping of postage stamps from scans.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-green.svg)
![OpenCV](https://img.shields.io/badge/Image%20Processing-OpenCV-orange.svg)

---
[Русская версия](README.md) | **English version**
---

## 📄 Description

**Markorez** is a desktop Python application that helps philatelists automatically find and extract postage stamps from scanned images. The program uses computer vision (OpenCV) to detect stamp contours and allows both automatic and manual selection of areas.

## ✨ Features

- **Automatic Stamp Search** — intelligent contour detection with adjustable parameters
- **Manual Mode** — ability to manually select missed stamps
- **Extraction and Saving** — automatic cropping and export to PNG/JPEG
- **Adding Captions** — ability to add descriptions to each stamp
- **Cyrillic Support** — works with Russian paths and text
- **Internationalization** — support for both English and Russian languages

## 🛠️ Installation

### Requirements

- Python 3.10+
- Windows/Linux/macOS

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/seoeaa/markorez.git
cd markorez
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

## 🚀 Usage

1. Click **"Open File"** to load a scan with stamps.
2. Adjust search parameters in the left panel:
   - Threshold — detection sensitivity
   - Min Area — filter for small objects
   - Dilation Radius — to merge close contours
3. Click **"Find and Separate"** for automatic search.
4. Use **"Drawing Mode"** for manual selection if needed.
5. Click **"Extract"** to crop the found stamps.
6. Add captions (optional) and save the results.
7. You can switch the language in the top menu (requires restart).

## 📂 Project Structure

```
markorez/
├── main.py              # Main application file
├── i18n.py              # Internationalization logic
├── editor_window.py    # Stamp editor window
├── canvas_widget.py    # Canvas widget for drawing
├── image_utils.py      # Image processing utilities
├── constants.py        # Constants and settings
├── requirements.txt    # Python dependencies
├── build.bat          # Build script for exe (Windows)
└── Markorez.spec      # PyInstaller specification
```

## 📦 Building executable

To create a standalone executable:
```bash
pip install pyinstaller
pyinstaller Markorez.spec
```

Or use the provided script on Windows:
```bash
build.bat
```

## 📚 Dependencies

- `customtkinter` — modern GUI
- `opencv-python-headless` — image processing
- `numpy` — numerical computations
- `Pillow` — image handling
- `pyinstaller` — executable creation

## 💬 Support

For questions and suggestions: [@slaveaa](https://t.me/slaveaa)

## 📜 License

MIT License

## 👤 Author

seoeaa
