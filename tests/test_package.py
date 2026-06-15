import importlib.metadata
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_version_exported():
    import mesadigital

    assert hasattr(mesadigital, "__version__")
    assert re.match(r"^\d+\.\d+\.\d+", mesadigital.__version__)


def test_version_matches_metadata():
    import mesadigital

    assert mesadigital.__version__ == importlib.metadata.version("mesadigital")


def test_console_script_entry_point():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with open(ROOT / "pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    scripts = config.get("project", {}).get("scripts", {})
    assert "mesadigital-api" in scripts


def test_alembic_env_imports_target_metadata():
    alembic_env = (ROOT / "alembic" / "env.py").read_text()
    assert "from mesadigital.api.db.models import target_metadata" in alembic_env


def test_gitignore_entries():
    gitignore = (ROOT / ".gitignore").read_text()
    required = ["__pycache__", "*.pyc", ".env", "dev.db", "dist/", ".mypy_cache/"]
    for entry in required:
        assert entry in gitignore, f"Missing .gitignore entry: {entry}"


def test_app_importable():
    from mesadigital.api.main import app

    assert app is not None


def test_target_metadata_exists():
    from mesadigital.api.db.models import target_metadata

    assert target_metadata is not None
