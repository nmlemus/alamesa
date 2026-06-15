import os

DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
