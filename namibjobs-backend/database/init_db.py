from database import engine, Base
import models  # noqa: F401 — ensures models are registered on Base


def init():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init()
