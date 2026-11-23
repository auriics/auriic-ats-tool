import os
import sys

# Ensure root directory is on PYTHONPATH for Vercel
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app
from backend.database.db import init_db

try:
    init_db()
except Exception as e:
    print(f"Vercel serverless init_db notice: {e}")
