import sys
from pathlib import Path

# Ensure the backend package root is importable when Vercel runs this file
# from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: F401,E402

# Vercel's Python runtime picks up `app` from this module.
