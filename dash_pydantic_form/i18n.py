import gettext
import os
from contextlib import contextmanager
from functools import partial
from pathlib import Path

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "fr"]

locale_dir = str(Path(__file__).parent / "locales")
gettext.bindtextdomain("pydf", locale_dir)


@contextmanager
def language_context(language: str):
    """Language context for pydf."""
    language_before = os.getenv("LANGUAGE")
    os.environ["LANGUAGE"] = language
    try:
        yield
    finally:
        os.environ["LANGUAGE"] = language_before


_ = partial(gettext.dgettext, "pydf")
