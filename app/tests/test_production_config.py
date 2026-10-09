import os
import pytest
from fastapi import HTTPException
from app.db.session import get_db_url
from app.services.storage import StorageService

def test_vercel_entrypoint_import() -> None:
    from api.index import app_handler, app
    assert app is not None
    assert app_handler is not None

def test_database_url_postgresql_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_SQLITE", "false")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:secret@postgres.host.com:5432/production_db")
    
    resolved_url = get_db_url()
    assert resolved_url.startswith("postgresql://")
    assert "postgres.host.com" in resolved_url

def test_storage_service_unconfigured_s3_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.STORAGE_METHOD", "s3")
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    
    with pytest.raises(HTTPException) as exc_info:
        StorageService.save_file(b"data", "samples", "test.png")
    assert exc_info.value.status_code == 503
    assert "S3 storage is selected" in exc_info.value.detail

def test_storage_service_unconfigured_cloudinary_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.STORAGE_METHOD", "cloudinary")
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    
    with pytest.raises(HTTPException) as exc_info:
        StorageService.save_file(b"data", "samples", "test.png")
    assert exc_info.value.status_code == 503
    assert "Cloudinary storage is selected" in exc_info.value.detail

def test_storage_service_local_file_success(tmp_path) -> None:
    test_subfolder = "test_samples"
    test_filename = "sample_test.png"
    contents = b"fake_png_data"
    
    file_path, public_url = StorageService.save_file(contents, test_subfolder, test_filename)
    assert os.path.exists(file_path)
    assert public_url.endswith(f"{test_subfolder}/{test_filename}")
    
    deleted = StorageService.delete_file(file_path)
    assert deleted is True
    assert not os.path.exists(file_path)
