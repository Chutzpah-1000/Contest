from __future__ import annotations

from pathlib import Path

import app
import app.components
import app.services
import etl
import etl.extract
import etl.transform
import models
import models.forecast
import models.matching


def test_expected_packages_are_importable() -> None:
    packages = [
        app,
        app.components,
        app.services,
        etl,
        etl.extract,
        etl.transform,
        models,
        models.forecast,
        models.matching,
    ]

    assert all(package.__name__ for package in packages)


def test_local_secrets_are_ignored() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".streamlit/secrets.toml" in gitignore
    assert ".env" in gitignore
