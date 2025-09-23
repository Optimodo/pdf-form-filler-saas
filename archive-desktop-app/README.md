# PDF Form Filler

A user-friendly tool for batch-filling PDF forms using data from CSV files. Designed for construction and office workflows, with a simple interface and robust output options.

## Features
- Fill multiple PDF forms automatically from CSV data
- Batch processing for efficiency
- Custom output location
- Modern, easy-to-use GUI (PySide6)
- Built-in quick instructions and detailed manual

## Requirements
- Python 3.8+
- Windows OS (for GUI and packaging)
- See `requirements.txt` for Python dependencies

## Setup & Usage
1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-org/pdf-form-filler.git
   cd pdf-form-filler
   ```
2. **Create and activate a virtual environment (recommended):**
   ```sh
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # or
   source venv/bin/activate  # On Mac/Linux
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Run the program:**
   ```sh
   python pdf_filler_gui.py
   ```

## Building the Executable
To create a standalone Windows executable (not included in this repo):
1. Ensure you have [PyInstaller](https://pyinstaller.org/) installed:
   ```sh
   pip install pyinstaller
   ```
2. Run the build script:
   ```sh
   python build_with_version.py
   ```
   The executable will be created in the `dist/` folder (not tracked by git).

## Distribution
- The compiled `.exe` is **not included** in this repository due to size limits and best practices.
- For end users, a release ZIP is created containing the executable, manual, instructions, and templates.

## Documentation
- See the included manual PDF for full instructions and advanced features.
- For a quick start, refer to the `INSTRUCTIONS-READ-ME.txt` in the release package.

## Contact
**Developer:** Mike McLean  
**Company:** Malcolm Building Services  
**Email:** mike.mclean@malcolmbuildingservices.co.uk 