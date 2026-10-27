import uuid

import pytest

from app import db
from app.models import Blacklist

EMAIL = "cliente@example.com"


@pytest.fixture
def email_bloqueado(app):
    """Inserta el email directo en la base, sin depender del POST."""
    with app.app_context():
        db.session.add(
            Blacklist(
                email=EMAIL,
                app_uuid=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
                blocked_reason="Solicitud del cliente",
                ip_address="203.0.113.5",
            )
        )
        db.session.commit()
    return EMAIL


def test_get_bloqueado(client, auth_headers, email_bloqueado):
    response = client.get(f"/blacklists/{email_bloqueado}", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {"is_blacklisted": True, "blocked_reason": "Solicitud del cliente"}


def test_get_no_bloqueado(client, auth_headers):
    response = client.get("/blacklists/otro@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {"is_blacklisted": False, "blocked_reason": None}


def test_get_mayusculas(client, auth_headers, email_bloqueado):
    response = client.get(f"/blacklists/{email_bloqueado.upper()}", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["is_blacklisted"] is True


def test_get_sin_token(client, email_bloqueado):
    response = client.get(f"/blacklists/{email_bloqueado}")

    assert response.status_code == 401
