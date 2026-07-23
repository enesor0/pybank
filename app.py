"""PyBank Flet uygulama giriş noktası."""

from pathlib import Path

from pybank.bootstrap import build_application
from pybank.presentation.flet_app import run_flet


if __name__ == "__main__":
    application = build_application(Path(__file__).with_name("pybank.sqlite3"))
    run_flet(application)
