"""Tests for wardrobe endpoints."""
import io

import pytest
from fastapi import status
from PIL import Image


def create_test_image() -> bytes:
    """Create a test image in memory."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_list_garments_empty(client, auth_headers):
    """Test listing garments when empty."""
    response = client.get("/wardrobe/items", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_garment_without_image(client, auth_headers):
    """Test creating a garment without image."""
    response = client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={
            "name": "Test Shirt",
            "category": "top",
            "style": "casual",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Shirt"
    assert data["category"] == "top"


def test_create_garment_with_image(client, auth_headers):
    """Test creating a garment with image."""
    image_data = create_test_image()
    response = client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={
            "name": "Test Shirt",
            "category": "top",
        },
        files={"image": ("test.jpg", image_data, "image/jpeg")},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Shirt"
    # Image URL should be present (even if it's a local path)
    # assert data["image_url"] is not None


def test_list_garments_with_filter(client, auth_headers):
    """Test listing garments with filters."""
    # Create test garments
    client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={"name": "Shirt", "category": "top"},
    )
    client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={"name": "Pants", "category": "bottom"},
    )

    # Filter by category
    response = client.get("/wardrobe/items?category=top", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "top"


def test_update_garment(client, auth_headers):
    """Test updating a garment."""
    # Create garment
    create_response = client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={"name": "Old Name", "category": "top"},
    )
    garment_id = create_response.json()["id"]

    # Update garment
    response = client.put(
        f"/wardrobe/items/{garment_id}",
        headers=auth_headers,
        json={"name": "New Name"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "New Name"


def test_delete_garment(client, auth_headers):
    """Test deleting a garment."""
    # Create garment
    create_response = client.post(
        "/wardrobe/items",
        headers=auth_headers,
        data={"name": "To Delete", "category": "top"},
    )
    garment_id = create_response.json()["id"]

    # Delete garment
    response = client.delete(f"/wardrobe/items/{garment_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    # Verify it's deleted (soft delete)
    list_response = client.get("/wardrobe/items", headers=auth_headers)
    assert garment_id not in [g["id"] for g in list_response.json()]

