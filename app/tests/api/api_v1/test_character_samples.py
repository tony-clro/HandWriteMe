import io
import os
from fastapi.testclient import TestClient

from app.core.config import settings


def _create_test_profile(client: TestClient) -> int:
    res = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "Sample Test Profile", "description": "Profile for sample testing"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_upload_character_sample_success(client: TestClient) -> None:
    profile_id = _create_test_profile(client)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    response = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "A", "sample_type": "image"},
        files={"file": ("letter_a.png", io.BytesIO(fake_png), "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["profile_id"] == profile_id
    assert data["character"] == "A"
    assert data["sample_type"] == "image"
    assert "file_path" in data
    assert data["image_url"] is not None
    assert os.path.exists(data["file_path"])


def test_list_character_samples(client: TestClient) -> None:
    profile_id = _create_test_profile(client)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    # Upload two samples
    client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "X"},
        files={"file": ("x.png", io.BytesIO(fake_png), "image/png")},
    )
    client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "Y"},
        files={"file": ("y.png", io.BytesIO(fake_png), "image/png")},
    )

    response = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) >= 2
    chars = [s["character"] for s in samples]
    assert "X" in chars
    assert "Y" in chars


def test_get_character_sample_by_id(client: TestClient) -> None:
    profile_id = _create_test_profile(client)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    upload_res = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "Z"},
        files={"file": ("z.png", io.BytesIO(fake_png), "image/png")},
    ).json()

    sample_id = upload_res["id"]
    response = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples/{sample_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_id
    assert data["character"] == "Z"


def test_delete_character_sample(client: TestClient) -> None:
    profile_id = _create_test_profile(client)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    upload_res = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "9"},
        files={"file": ("nine.png", io.BytesIO(fake_png), "image/png")},
    ).json()

    sample_id = upload_res["id"]
    file_path = upload_res["file_path"]

    # Delete sample
    del_res = client.delete(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples/{sample_id}")
    assert del_res.status_code == 204

    # Verify file deleted on disk
    assert not os.path.exists(file_path)

    # Verify 404 on GET
    get_res = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples/{sample_id}")
    assert get_res.status_code == 404


def test_upload_invalid_file_type(client: TestClient) -> None:
    profile_id = _create_test_profile(client)
    text_file = b"This is plain text, not an image"

    response = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples",
        data={"character": "A"},
        files={"file": ("document.txt", io.BytesIO(text_file), "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_sample_missing_profile(client: TestClient) -> None:
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    response = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles/999999/samples",
        data={"character": "A"},
        files={"file": ("a.png", io.BytesIO(fake_png), "image/png")},
    )
    assert response.status_code == 404
    assert "Handwriting profile not found" in response.json()["detail"]


def test_get_or_delete_missing_sample(client: TestClient) -> None:
    profile_id = _create_test_profile(client)

    get_res = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples/999999")
    assert get_res.status_code == 404

    del_res = client.delete(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}/samples/999999")
    assert del_res.status_code == 404
