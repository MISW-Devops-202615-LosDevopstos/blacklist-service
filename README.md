# Blacklist Service

Microservicio REST para gestionar la lista negra global de emails de la organización. Las aplicaciones internas pueden agregar emails a la lista y consultar si un email está bloqueado.

Entrega 1 del curso de DevOps (Universidad de los Andes): despliegue manual en AWS Elastic Beanstalk con PostgreSQL en RDS.

**Stack:** Python 3.11+, Flask, Flask-SQLAlchemy, Flask-RESTful, Flask-Marshmallow, Flask-JWT-Extended, Werkzeug, PostgreSQL (psycopg 3) y Gunicorn.

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/blacklists` | Bearer token | Agrega un email a la lista negra |
| GET | `/blacklists/<email>` | Bearer token | Indica si un email está en la lista y el motivo |
| GET | `/ping` | Ninguna | Health check; devuelve la versión desplegada |

**POST /blacklists**

```json
{
  "email": "cliente@example.com",
  "app_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "blocked_reason": "Solicitud del cliente"
}
```

- `email`: obligatorio, formato válido. Se guarda en minúsculas.
- `app_uuid`: obligatorio, UUID válido.
- `blocked_reason`: opcional, máximo 255 caracteres.
- El servicio guarda además la IP de origen y la fecha/hora (UTC) de la solicitud.

| Código | Respuesta |
|---|---|
| 201 | `{"msg": "Email agregado a la lista negra"}` |
| 400 | `{"msg": "Datos inválidos", "errors": {...}}` |
| 401 | Token ausente o inválido |
| 409 | `{"msg": "El email ya está en la lista negra"}` |

**GET /blacklists/<email>**

```json
{"is_blacklisted": true, "blocked_reason": "Solicitud del cliente"}
```

Si el email no está: `{"is_blacklisted": false, "blocked_reason": null}`. Sin token o con token inválido: 401.

**GET /ping**

```json
{"status": "ok", "version": "1.0.0"}
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | `postgresql://<usuario>:<clave>@<host>:5432/<base_de_datos>` |
| `JWT_SECRET_KEY` | Sí | Llave para firmar y validar el token. Mínimo 32 caracteres |

La versión que muestra `/ping` no es una variable de entorno: se lee del archivo `VERSION` en la raíz del repo.

Generar una llave segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Si falta una variable obligatoria, la app no arranca y muestra cuál falta. La tabla `blacklist` se crea automáticamente al iniciar.

## Correr en local

Requisitos: Python 3.11+, Docker.

```bash
# 1. Base de datos PostgreSQL
docker compose up -d

# 2. Entorno virtual y dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Variables de entorno (completar JWT_SECRET_KEY en .env)
cp .env.example .env
set -a; source .env; set +a

# 4. Servidor
gunicorn --bind :8000 --workers 2 application:application
```

Si el puerto 5432 está ocupado por otro contenedor, deténgalo o cambie el puerto en `docker-compose.yml` y en `DATABASE_URL`.

## Token de autenticación

El token es un JWT estático sin expiración, firmado con `JWT_SECRET_KEY`:

```bash
python generate_token.py
```

Se envía en el header `Authorization: Bearer <token>`. El token solo es válido con la misma `JWT_SECRET_KEY` con la que se generó: si la llave cambia, hay que generar uno nuevo. No suba el token al repositorio ni lo comparta por chat.

## Pruebas con Postman

1. Importe los dos archivos de `postman/` (colección y environment).
2. Seleccione el environment **Blacklist Service**.
3. Configure `base_url` (`http://localhost:8000` o la URL de Beanstalk) y pegue el token en `token`, **solo en Current/Local value**.
4. Ejecute la colección completa con *Run collection*. Son 11 escenarios y 19 pruebas.

## Pruebas unitarias

Las pruebas usan pytest con SQLite en memoria, así que no necesitan Docker, RDS ni variables de entorno:

```bash
pip install -r requirements-dev.txt
pytest -v
```

| Archivo | Escenarios |
|---|---|
| `tests/test_blacklists_post.py` | 8: creación válida, motivo opcional, guarda IP y fecha, email/`app_uuid`/motivo inválidos (400), sin token (401) y duplicado (409) |
| `tests/test_blacklists_get.py` | 4: email bloqueado, no bloqueado, consulta en mayúsculas y sin token (401) |
| `tests/test_ping.py` | 1: responde la versión sin token |

`tests/conftest.py` crea una app nueva por prueba (base vacía) y un token firmado con una llave de prueba, no con la real.

## Integración continua

Cada commit en `main` dispara el pipeline:

```
commit a main → CodePipeline → CodeBuild (buildspec.yml) → artefacto .zip en S3
```

El `buildspec.yml` instala dependencias con Python 3.13, ejecuta `pytest`, publica el informe de pruebas en CodeBuild y arma el artefacto con los mismos archivos del despliegue manual. Si una prueba falla, el build falla y no se genera el artefacto.

No hay despliegue automático (CD): el artefacto se despliega a mano en Beanstalk, como se describe abajo. Puede usarse el `.zip` que genera CodeBuild en S3 o generarlo localmente.

El artefacto queda en el bucket de artefactos del pipeline, en la carpeta `blacklist-service-ci/BuildArtif/`. El objeto tiene un nombre aleatorio y no tiene extensión, pero es un `.zip`. Para revisarlo, se descarga y se abre con `unzip -l <archivo>`.

## Despliegue en Elastic Beanstalk

Generar el paquete desde la raíz del repo:

```bash
zip -r deploy.zip application.py Procfile requirements.txt VERSION app -x "*__pycache__*"
```

El `.zip` incluye solo el código necesario, con los archivos en la raíz. No incluye `venv/`, `.git/`, `.env`, `postman/` ni `docker-compose.yml`.

Configuración del ambiente:

- Plataforma: **Python 3.11 o superior en Amazon Linux 2023**.
- Variables de entorno: `DATABASE_URL` (endpoint de RDS) y `JWT_SECRET_KEY`.
- Health check del load balancer: ruta `/ping`.
- RDS debe aceptar conexiones al puerto 5432 desde el security group de las instancias de Beanstalk.
- El `Procfile` arranca Gunicorn en el puerto 8000, el que usa por defecto el proxy de la plataforma.

### Desplegar una versión nueva

La versión viaja dentro del `.zip` (archivo `VERSION`). Así, cambiarla implica un despliegue de código y Beanstalk aplica la política de despliegue configurada (All at once, Rolling, Immutable…). Cambiar una variable de entorno, en cambio, es un cambio de configuración y no usa esa política.

```bash
echo "1.0.1" > VERSION
git commit -am "chore: versión 1.0.1"
zip -r deploy.zip application.py Procfile requirements.txt VERSION app -x "*__pycache__*"
```

Luego, en Beanstalk: *Cargar e implementar* → `deploy.zip` con etiqueta `v1.0.1`. Durante el despliegue, `/ping` muestra qué instancias ya responden la versión nueva.

## Estructura

```
├── app/
│   ├── __init__.py      # Application factory, JWT y rutas
│   ├── config.py        # Configuración desde variables de entorno
│   ├── models.py        # Modelo de la tabla blacklist
│   ├── resources.py     # Endpoints
│   └── schemas.py       # Validación de entrada
├── tests/               # Pruebas unitarias (pytest)
│   ├── conftest.py      # App de prueba, cliente y token
│   ├── test_blacklists_get.py
│   ├── test_blacklists_post.py
│   └── test_ping.py
├── postman/             # Colección y environment de Postman
├── application.py       # Punto de entrada para Beanstalk/Gunicorn
├── buildspec.yml        # Instrucciones de build para AWS CodeBuild
├── generate_token.py    # Genera el token JWT estático
├── Procfile
├── VERSION              # Versión que muestra /ping
├── requirements.txt
├── requirements-dev.txt # Dependencias de desarrollo (pytest)
├── pytest.ini           # Configuración de pytest
├── docker-compose.yml   # PostgreSQL para desarrollo local
└── .env.example
```

## Convención de commits

Se usa [Conventional Commits](https://www.conventionalcommits.org/) con la descripción en español e imperativo:

```
<tipo>(<alcance opcional>): <descripción>
```

Tipos: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `build`. Ejemplo: `feat(api): agrega endpoint POST /blacklists`.

Flujo de trabajo: ramas `feature/...` y Pull Request hacia `main` con al menos una aprobación.
