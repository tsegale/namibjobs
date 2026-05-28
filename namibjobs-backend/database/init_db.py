import sys
from pathlib import Path

# Remove the script's own dir so 'database.py' doesn't shadow the package
_here = str(Path(__file__).resolve().parent)
if _here in sys.path:
    sys.path.remove(_here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database import engine, Base
import database.models  # noqa: F401 — registers models on Base


def init():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init()
