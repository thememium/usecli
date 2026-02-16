"""Debug conftest import."""

import sys
from pathlib import Path

print("DEBUG: conftest.py is being loaded")
print("DEBUG: sys.path before insert:", sys.path[:3])

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("DEBUG: sys.path after insert:", sys.path[:3])
print("DEBUG: src directory:", str(Path(__file__).parent.parent / "src"))
