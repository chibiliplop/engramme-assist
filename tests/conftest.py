import sys
from pathlib import Path

# Make the repo root importable so `import engramme_assist` works without an
# editable install during the TDD loop.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
