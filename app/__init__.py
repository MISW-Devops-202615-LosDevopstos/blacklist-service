from flask import Flask
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.config import Config

db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _validate_config(app)

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)

    _register_routes(app)

    with app.app_context():
        from app import models  # noqa: F401  registra la tabla antes de crearla
        try:
            db.create_all()
        except (IntegrityError, ProgrammingError):
            # Otra instancia o worker creó la tabla al mismo tiempo: ya existe
            pass

    return app


def _validate_config(app):
    required = {"SQLALCHEMY_DATABASE_URI": "DATABASE_URL", "JWT_SECRET_KEY": "JWT_SECRET_KEY"}
    missing = [env for key, env in required.items() if not app.config.get(key)]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")


def _register_routes(app):
    from app.resources import BlacklistResource, BlacklistDetailResource, PingResource

    api = Api(app)
    api.add_resource(BlacklistResource, "/blacklists")
    api.add_resource(BlacklistDetailResource, "/blacklists/<string:email>")
    api.add_resource(PingResource, "/ping")


@jwt.unauthorized_loader
def _missing_token(reason):
    return {"msg": "Token de autorización requerido"}, 401


@jwt.invalid_token_loader
def _invalid_token(reason):
    return {"msg": "Token inválido"}, 401
