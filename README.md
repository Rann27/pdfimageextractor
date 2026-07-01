# PDF Image Extractor

A modern desktop application to extract all embedded images from **PDF** and **EPUB** files — instantly, with a clean glassy UI.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?logo=qt&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24%2B-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Features

- **Drag & Drop** — drop a PDF or EPUB directly onto the window
- **Click to Browse** — click the drop zone to open a file picker
- **Auto-save** — extracted images are saved in a folder next to the source file, named after the file
- **Live preview** — responsive 5-column thumbnail grid updates in real time as images are extracted
- **Background processing** — UI never freezes; extraction runs on a separate thread
- **Multi-format output** — preserves original format: JPG, PNG, TIFF, WebP, SVG, GIF, BMP
- **Open Folder** — one-click to reveal the output folder in Explorer
- **Modern Glassy UI** — dark theme with animated drop zone, gradient progress bar, and ambient orb lighting

---

## Supported Input Formats

| Format | Notes |
|--------|-------|
| `.pdf` | Extracts all embedded raster images (JPG, PNG, TIFF, etc.) |
| `.epub` | Scans the internal ZIP structure and extracts all image assets |

---

## Output Structure

Given a file called `MyBook.pdf` located at `D:\Documents\MyBook.pdf`, the app creates:

```
D:\Documents\
├── MyBook.pdf
└── MyBook\
    ├── p001_0001.jpg
    ├── p001_0002.png
    ├── p002_0003.jpg
    └── ...
```

For EPUB files:

```
D:\Documents\
├── MyBook.epub
└── MyBook\
    ├── img_0001.jpg
    ├── img_0002.png
    └── ...
```

---

## Requirements

- **Python 3.10 or newer**
- **Windows** (tested on Windows 11); macOS/Linux should work with minor tweaks to the launcher

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Rann27/pdfimageextractor.git
cd pdfimageextractor
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Install dependencies

```bash
# Windows
.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
.venv/bin/pip install -r requirements.txt
```

Dependencies installed:

| Package | Version | Purpose |
|---------|---------|---------|
| `PyQt6` | ≥ 6.6.0 | Desktop GUI framework |
| `PyMuPDF` | ≥ 1.24.0 | PDF parsing and image extraction |
| `Pillow` | ≥ 10.0.0 | Image utilities |

---

## Running the App

### Windows (recommended)

Double-click **`run.bat`** — it automatically uses the project's `.venv`.

### Manual

```bash
# Windows
.venv\Scripts\python main.py

# macOS / Linux
.venv/bin/python main.py
```

---

## How to Use

1. **Launch** the app via `run.bat` or the command above
2. **Drop** a `.pdf` or `.epub` file onto the drop zone — or click the zone to browse
3. **Watch** the progress bar and live thumbnail grid as images are extracted
4. **Done** — a success message shows the total count; click **Open Folder** to see the results

> The output folder is created automatically in the same directory as your source file.

---

## Project Structure

```
pdfimageextractor/
├── main.py            # Full application (UI + worker thread + extraction logic)
├── requirements.txt   # Python dependencies
├── run.bat            # One-click launcher for Windows (uses .venv)
└── .venv/             # Virtual environment (not committed)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI Framework | PyQt6 |
| PDF Extraction | PyMuPDF (fitz) |
| EPUB Extraction | `zipfile` (Python stdlib) |
| Image Handling | Pillow |
| Threading | `QThread` (PyQt6) |

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

---

## License

[MIT](https://choosealicense.com/licenses/mit/)
