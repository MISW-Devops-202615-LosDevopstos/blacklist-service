import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.config import Config


class PruebasConfig(Config):
    """Configuración solo para pruebas: SQLite en memoria y una llave falsa."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    JWT_SECRET_KEY = "llave-solo-para-pruebas-no-es-la-real-32+"


@pytest.fixture
def app():
    app = create_app(PruebasConfig)
    yield app
    with app.app_context():
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity="pytest")
    return {"Authorization": f"Bearer {token}"}
