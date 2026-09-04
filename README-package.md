# Packaging the app

## 1) Build the executable

From the project root, run:

```bash
python package_app.py
```

This will:
- install PyInstaller if needed
- package the app into a single Windows executable
- create a desktop shortcut on the Windows Desktop

## 2) Desktop shortcut

The script creates a shortcut named:

```text
Marketing Booster.lnk
```

## 3) Notes

- The packaged app reads and writes the client data file next to the executable if present.
- If no data file is found, it will create one in the executable folder.
