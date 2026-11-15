from flask import current_app, request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Blacklist
from app.schemas import blacklist_schema


def _client_ip():
    # Detrás del load balancer de Beanstalk la IP real llega en X-Forwarded-For (primer valor)
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr


class BlacklistResource(Resource):
    @jwt_required()
    def post(self):
        try:
            data = blacklist_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"msg": "Datos inválidos", "errors": err.messages}, 400

        entry = Blacklist(**data, ip_address=_client_ip())
        db.session.add(entry)
        try:
            db.session.commit()
        except IntegrityError:
            # La restricción unique del email detectó un duplicado
            db.session.rollback()
            return {"msg": "El email ya está en la lista negra"}, 409

        return {"msg": "Email agregado a la lista negra"}, 201


class BlacklistDetailResource(Resource):
    @jwt_required()
    def get(self, email):
        entry = db.session.scalar(
            db.select(Blacklist).filter_by(email=email.strip().lower())
        )
        if entry is None:
            return {"is_blacklisted": False, "blocked_reason": None}, 200
        return {"is_blacklisted": True, "blocked_reason": entry.blocked_reason}, 200


class PingResource(Resource):
    def get(self):
        return {"status": "ok", "version": current_app.config["APP_VERSION"]}, 200
