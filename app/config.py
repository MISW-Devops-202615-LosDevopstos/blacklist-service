import os


class Config:
    # Cadena de conexión a PostgreSQL (RDS en Beanstalk, Docker en local)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Llave con la que se firma y verifica el token Bearer
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # Versión visible en /ping para identificar qué código corre en cada instancia
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
