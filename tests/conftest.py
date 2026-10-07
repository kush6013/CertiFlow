import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
import app.config as config


@pytest.fixture(scope="session")
def temp_test_dir():
    temp_dir = Path(tempfile.mkdtemp(prefix="test_cert_storage_"))
    original_storage = config.STORAGE_DIR
    config.STORAGE_DIR = temp_dir
    yield temp_dir
    # Cleanup
    config.STORAGE_DIR = original_storage
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_db(temp_test_dir):
    test_db_file = temp_test_dir / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_file}",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Teardown
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as test_client:
        yield test_client
