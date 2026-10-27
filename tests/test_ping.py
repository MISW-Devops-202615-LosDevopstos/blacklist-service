from pathlib import Path

VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()


def test_ping_sin_token(client):
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": VERSION}
