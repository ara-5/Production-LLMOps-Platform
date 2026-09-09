import pytest
from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
