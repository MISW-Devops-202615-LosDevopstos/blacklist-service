import os
import sys

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

secret = os.environ.get("JWT_SECRET_KEY")
if not secret:
    sys.exit("Falta la variable de entorno JWT_SECRET_KEY")

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = secret
JWTManager(app)

with app.app_context():
    # expires_delta=False: el token no expira (token estático que permite el enunciado)
    print(create_access_token(identity="postman", expires_delta=False))
