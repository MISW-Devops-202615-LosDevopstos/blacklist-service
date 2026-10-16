from marshmallow import fields, pre_load, validate

from app import ma
from app.models import Blacklist


class BlacklistSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Blacklist
        fields = ("email", "app_uuid", "blocked_reason")

    email = fields.Email(required=True, validate=validate.Length(max=254))

    @pre_load
    def normalize_email(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            data = {**data, "email": data["email"].strip().lower()}
        return data


blacklist_schema = BlacklistSchema()
