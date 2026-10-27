from app import db
from app.models import Blacklist

APP_UUID = "123e4567-e89b-12d3-a456-426614174000"


def _body(**cambios):
    """Body válido; cada prueba cambia solo lo que necesita."""
    body = {
        "email": "cliente@example.com",
        "app_uuid": APP_UUID,
        "blocked_reason": "Solicitud del cliente",
    }
    body.update(cambios)
    return body


def test_post_valido(client, auth_headers):
    response = client.post("/blacklists", json=_body(), headers=auth_headers)

    assert response.status_code == 201
    assert response.get_json() == {"msg": "Email agregado a la lista negra"}


def test_post_sin_motivo(client, auth_headers):
    body = _body()
    del body["blocked_reason"]

    response = client.post("/blacklists", json=body, headers=auth_headers)

    assert response.status_code == 201


def test_post_guarda_ip_y_fecha(app, client, auth_headers):
    headers = {**auth_headers, "X-Forwarded-For": "203.0.113.5"}

    client.post("/blacklists", json=_body(email="Cliente@Example.com"), headers=headers)

    with app.app_context():
        entry = db.session.scalar(db.select(Blacklist))
        assert entry.email == "cliente@example.com"
        assert entry.ip_address == "203.0.113.5"
        assert entry.created_at is not None


def test_post_email_invalido(client, auth_headers):
    response = client.post("/blacklists", json=_body(email="no-es-un-email"), headers=auth_headers)

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


def test_post_app_uuid_invalido(client, auth_headers):
    response = client.post("/blacklists", json=_body(app_uuid="123"), headers=auth_headers)

    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]


def test_post_motivo_largo(client, auth_headers):
    response = client.post("/blacklists", json=_body(blocked_reason="x" * 256), headers=auth_headers)

    assert response.status_code == 400
    assert "blocked_reason" in response.get_json()["errors"]


def test_post_sin_token(client):
    response = client.post("/blacklists", json=_body())

    assert response.status_code == 401


def test_post_duplicado(client, auth_headers):
    client.post("/blacklists", json=_body(), headers=auth_headers)

    response = client.post("/blacklists", json=_body(email="CLIENTE@EXAMPLE.COM"), headers=auth_headers)

    assert response.status_code == 409
