"""
Run once to add the embedding column to an existing jobs table.
Safe to run multiple times — skips if the column already exists.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from database.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='jobs' AND column_name='embedding'"
        ))
        if result.fetchone():
            print("Column 'embedding' already exists — skipping.")
            return

        conn.execute(text("ALTER TABLE jobs ADD COLUMN embedding JSON"))
        conn.commit()
        print("Column 'embedding' added successfully.")


if __name__ == "__main__":
    migrate()
