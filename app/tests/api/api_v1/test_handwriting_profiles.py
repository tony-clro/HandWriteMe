from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_handwriting_profile(client: TestClient) -> None:
    payload = {
        "profile_name": "Classic Cursive",
        "description": "A elegant cursive handwriting sample",
    }
    response = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["profile_name"] == payload["profile_name"]
    assert data["description"] == payload["description"]
    assert "created_at" in data


def test_list_handwriting_profiles(client: TestClient) -> None:
    # Create two profiles
    client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "Profile Alpha", "description": "First profile"},
    )
    client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "Profile Beta", "description": "Second profile"},
    )

    response = client.get(f"{settings.API_V1_STR}/handwriting-profiles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    names = [item["profile_name"] for item in data]
    assert "Profile Alpha" in names
    assert "Profile Beta" in names


def test_get_handwriting_profile_by_id(client: TestClient) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "Specific Profile", "description": "Target profile"},
    ).json()

    profile_id = created["id"]
    response = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["profile_name"] == "Specific Profile"
    assert data["description"] == "Target profile"


def test_get_handwriting_profile_not_found(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/handwriting-profiles/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Handwriting profile not found"


def test_create_handwriting_profile_validation_error(client: TestClient) -> None:
    # Missing required 'profile_name' field
    response = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"description": "Missing profile name"},
    )
    assert response.status_code == 422


def test_update_handwriting_profile(client: TestClient) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "Original Name", "description": "Original Description"},
    ).json()
    profile_id = created["id"]

    update_res = client.put(
        f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}",
        json={"profile_name": "Updated Name"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["profile_name"] == "Updated Name"
    assert updated_data["description"] == "Original Description"


def test_delete_handwriting_profile(client: TestClient) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/handwriting-profiles",
        json={"profile_name": "To Be Deleted", "description": "Delete me"},
    ).json()
    profile_id = created["id"]

    del_res = client.delete(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"{settings.API_V1_STR}/handwriting-profiles/{profile_id}")
    assert get_res.status_code == 404

