# AI Data Extractor from Documents 0.1.0
English | [Русский](README.md)

AI Data Extractor from Documents is an application for extracting structured data from procurement documentation and other tender related documents. The tool helps automatically identify the required sections and convert them into structured JSON. In particular, it can highlight key tender information such as deadlines, contract price, participants, and submission rules. The extracted data is presented in an easy to read and reusable report format. This significantly simplifies bureaucratic routines for teams that work with large volumes of documents on a daily basis.

The solution is available in two usage modes:

* Graphical interface (GUI) where you can work entirely with mouse clicks.
* Command line interface (CLI) designed for automation and integration into scripts.

---

## Capabilities

* Finds, highlights, and structures data in uploaded documents.
* Automatically detects tender requisites and deadlines, contract price, and submission requirements.
* Saves individual sections (blocks) and exports them to JSON for further processing.

---

## Components

* Graphical desktop application (`app/main.py`) for working with documents through the interface.
* Command line client (`cli.py`) to automate workflows in scripts and pipelines.
* Persistent storage of extracted data with the `--save-dir` option.
* Project settings and constants are located in `infra/config.py`.

---

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

---

## Running the GUI

```bash
python app/main.py
```

A window with the main interface will open. Select the documents you want to process and run the extraction.

GUI preview:

![GUI Example](docs/images/gui_example.png)

By default, the document log is displayed so you can track the status of the extraction step by step.

---

## Running the CLI

```bash
python cli.py <file1> <file2> ...
```

Useful arguments:

* `--no-wait-index` - runs without waiting for the search index to finish building.
* `--save-dir <path>` - saves results to the specified directory.

The CLI outputs the extracted data to the console and simultaneously stores it in JSON. This is convenient for automation and quick checks.

---

## Data Storage

* All logs are located at `results/logs/vector_store_journal.jsonl`.
* When `--save-dir` is specified, the processed files are copied and saved to that directory.

---

## Prompt Engineering

* The main extraction prompt for tender documents is stored in `prompts/tender_extractor_system.prompt.md`.
* You can replace this file with your own instructions if you need to process a different type of documents.

---

## Domain Expertise

* The project encapsulates experience with Excel, PowerShell, VBA, and related tooling.
* The solution allows you to automate typical tender analysis tasks in Excel and no code environments.

---

## Distribution (optional)

You can package the CLI into a standalone executable using PyInstaller:

```bash
pyinstaller --onefile cli.py
```

The resulting binary will appear in the `dist` directory.

---

## Release Notes

**Version 0.1.0**

* Added graphical application and command line client.
* Implemented automatic extraction of requisites, deadlines, and other tender details in JSON.
* Enabled saving data and setting up persistent storage.

---

## Roadmap

* Integrate connectors for additional outputs (Excel, webhooks).
* Add automated tests and CI pipeline.
* Expand the prompt library for different document types.

---

## Configuration

An OpenAI ChatGPT API key is required.
The key is expected at `C:/API_keys/API_key_GPT.txt`. Example of loading it:

```python
import os

API_KEY_PATH = os.path.join("C:\\", "API_keys", "API_key_GPT.txt")
with open(API_KEY_PATH, "r") as f:
    OPENAI_API_KEY = f.read().strip()
```

Alternatively, you can set the key directly in `infra/config.py`:

```python
OPENAI_API_KEY = "your_api_key_here"
```

Recommendation: keep secrets out of the repository and read them from the environment at runtime:

```python
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```
