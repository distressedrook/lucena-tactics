"""Root conftest: put the repo root on sys.path so `tests/` can import `src`
as a package (`from src.poisoned_line_detector import ...`) regardless of how
pytest is invoked.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
