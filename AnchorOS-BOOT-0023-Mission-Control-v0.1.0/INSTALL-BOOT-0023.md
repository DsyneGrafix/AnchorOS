# BOOT-0023 Installation — Linux Mint / Ubuntu

## Requirements

- Python 3.10 or newer
- A graphical web browser for automatic dashboard launch
- No third-party Python packages are required

## Install

1. Extract the ZIP archive.
2. Open a terminal in the extracted repository.
3. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Run the automated tests:

```bash
python -m unittest discover -s tests -v
```

5. Run a noninteractive boot verification:

```bash
python app.py --verify-only --no-browser
```

6. Start AnchorOS normally:

```bash
python app.py
```

Mission Control will start and the default browser will open. Press `Ctrl+C` in the terminal to stop Mission Control and shut down AnchorOS cleanly.

## Options

```bash
python app.py --no-browser
python app.py --verify-only --no-browser
```

If port 8080 is occupied, Mission Control tries ports 8081 through 8090 and prints the selected URL.
