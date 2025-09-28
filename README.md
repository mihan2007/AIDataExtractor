# VectorStore Toolkit 0.1.0

VectorStore Toolkit provides two entry points for interacting with the project data: a desktop GUI built on Tkinter and a CLI suited for automation and integrations. This release freezes the initial feature set before adding environment-specific examples.

## Features
- Tkinter GUI (`app/main.py`) for uploading documents and running extraction via Vector Store.
- CLI (`cli.py`) with progress logging, JSON output, and exit codes for automation.
- Optional saving of validated extraction results through `--save-dir`.
- Configuration defaults centralized in `infra/config.py`.

## Getting Started
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the GUI
```bash
python app/main.py
```
The GUI allows you to pick files, monitor progress, and view the extracted JSON result inline.

## Running the CLI
```bash
python cli.py <file1> <file2> ...
```
Key options:
- `--no-wait-index` — upload documents and exit without waiting for the extraction phase.
- `--save-dir <path>` — store the validated JSON output as a timestamped file.

Progress messages and the final summary are printed to stdout. Exit codes: `0` success, `1` upload failure, `2` missing `store_id`.

## External Integrations
- Automation tools (PowerShell, VBA, etc.) can call the CLI and watch stdout or monitor the saved JSON files.
- Future releases will include ready-to-use recipes for integrations with Excel, no-code platforms, and other runtimes.

## Packaging (Optional)
To distribute without Python on the target machine, use PyInstaller:
```bash
pyinstaller --onefile cli.py
```
Add `--add-data` for additional resources. The `dist` folder contains the portable executable.

## Release Notes
**Version 0.1.0**
- Initial GUI and CLI workflows completed.
- Logging, exit codes, and optional JSON persistence ready for integrations.
- Configuration surface prepared for future external overrides.

## Next Steps
- Document concrete integration samples (Excel VBA, web hooks).
- Add automated tests and CI scripts as the project evolves.
- Extend configuration handling with external files if required.
