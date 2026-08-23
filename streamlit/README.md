# BuildCipher Streamlit Compatibility Folder

This folder centralizes Streamlit-related entry scripts for easier maintenance.

## Entrypoints

- `web_app.py`
  - Compatibility wrapper (legacy v1 path)
- `web_app_v3.py`
  - Maintained Streamlit v3 entrypoint
- `web_app_v3_beautiful.py`
  - Compatibility wrapper for legacy v3 filename

## Legacy

- `legacy/web_app_enhanced_v2.py`
  - Deprecated Streamlit v2 monolithic app (kept for reference only)

## Run

Windows quick start from repository root:

```bat
start_streamlit.bat
```

The launcher will:

- verify Python 3.10+
- prefer `.buildcipher_runtime`, `.buildcipher_venv`, or `.venv`
- otherwise verify Poetry and run `poetry install` when backend dependencies are missing

From repository root:

```bash
python -m streamlit run streamlit/web_app.py --server.port=8503
```

Or run v3 directly:

```bash
python -m streamlit run streamlit/web_app_v3.py
```

## Notes

- Core Streamlit page modules live under:
  - `src/cipher_genius/ui/web_v3/`
- React frontend remains the primary maintained user interface:
  - `frontend/`
