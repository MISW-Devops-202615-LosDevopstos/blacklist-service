import os
from pathlib import Path


class Config:
    # Cadena de conexión a PostgreSQL (RDS en Beanstalk, Docker en local)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Deja que Flask-JWT-Extended responda sus errores (401) en vez de que Flask-RESTful los convierta en 500
    PROPAGATE_EXCEPTIONS = True

    # Llave con la que se firma y verifica el token Bearer
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # Versión visible en /ping. Viaja dentro del .zip (archivo VERSION) para que cambiarla
    # implique un despliegue de código y Beanstalk aplique la política de despliegue configurada
    APP_VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
