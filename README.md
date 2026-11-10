# Blacklist Service

Microservicio REST para gestionar la lista negra global de emails de la organización. Las aplicaciones internas pueden agregar emails a la lista y consultar si un email está bloqueado.

Proyecto del curso de DevOps (Universidad de los Andes):

| Entrega | Qué agrega |
|---|---|
| 1 | Despliegue manual en AWS Elastic Beanstalk con PostgreSQL en RDS |
| 2 | Pruebas unitarias e integración continua con CodePipeline y CodeBuild |
| 3 | Contenedores: la app corre en Amazon ECS Fargate y el pipeline construye y publica la imagen en ECR |

**Stack:** Python 3.13, Flask, Flask-SQLAlchemy, Flask-RESTful, Flask-Marshmallow, Flask-JWT-Extended, Werkzeug, PostgreSQL (psycopg 3), Gunicorn y Docker.

**AWS (región us-east-2):** RDS, ECR, ECS Fargate, Application Load Balancer, Systems Manager Parameter Store, CodePipeline, CodeBuild y Elastic Beanstalk.

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
{"status": "ok", "version": "1.0.4"}
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

En AWS las variables nunca van en texto plano en el repositorio: Fargate las lee de Parameter Store (ver [Despliegue en ECS Fargate](#despliegue-en-ecs-fargate)).

## Correr en local

Requisitos: Python 3.11+ y Docker. Primero, la base de datos y las variables:

```bash
docker compose up -d              # PostgreSQL local
cp .env.example .env              # completar JWT_SECRET_KEY
```

Si el puerto 5432 está ocupado por otro contenedor, deténgalo o cambie el puerto en `docker-compose.yml` y en `DATABASE_URL`.

### Con Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
set -a; source .env; set +a
gunicorn --bind :8000 --workers 2 application:application
```

### Con Docker (la misma imagen que corre en Fargate)

```bash
docker build -t blacklist-service .
docker run --rm -p 8000:8000 --env-file .env \
  -e DATABASE_URL=postgresql://blacklist:blacklist@host.docker.internal:5432/blacklist \
  --add-host=host.docker.internal:host-gateway \
  blacklist-service
```

Se sobrescribe `DATABASE_URL` porque dentro del contenedor `localhost` es el propio contenedor; `host.docker.internal` apunta al equipo donde corre el PostgreSQL de docker compose.

La imagen parte de `python:3.13-slim` (desde ECR Public, para evitar los límites de descarga de Docker Hub), instala solo `requirements.txt`, copia `application.py`, `VERSION` y `app/`, y corre Gunicorn en el puerto 8000 con un usuario sin privilegios. `.dockerignore` garantiza que `.env`, las pruebas y la colección de Postman no entren a la imagen.

## Token de autenticación

El token es un JWT estático sin expiración, firmado con `JWT_SECRET_KEY`:

```bash
python generate_token.py
```

Se envía en el header `Authorization: Bearer <token>`. El token solo es válido con la misma `JWT_SECRET_KEY` con la que se generó: si la llave cambia, hay que generar uno nuevo. No suba el token al repositorio ni lo comparta por chat.

## Pruebas con Postman

1. Importe los dos archivos de `postman/` (colección y environment).
2. Seleccione el environment **Blacklist Service**.
3. Configure `base_url` y pegue el token en `token`, **solo en Current/Local value**:
   - Local: `http://localhost:8000`
   - Fargate: `http://blacklist-alb-1344505848.us-east-2.elb.amazonaws.com`
   - Beanstalk: `http://Blacklist-service-env.eba-hteiwdmm.us-east-2.elasticbeanstalk.com`
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

Cada commit en `main` dispara dos pipelines, que comparten la conexión con GitHub y las mismas pruebas:

| Pipeline | Buildspec | Qué produce |
|---|---|---|
| `blacklist-service-ecs` (actual) | `buildspec-ecs.yml` | Imagen Docker en ECR + archivos para el despliegue en Fargate |
| `blacklist-service-ci` (entrega 2) | `buildspec.yml` | `.zip` para Beanstalk en S3 |

### Pipeline de contenedores (`blacklist-service-ecs`)

```
commit a main → CodePipeline → CodeBuild (buildspec-ecs.yml) → imagen en ECR + artefacto en S3
```

| Fase | Qué hace |
|---|---|
| `install` | Python 3.13 e instala `requirements-dev.txt` |
| `pre_build` | Calcula la dirección de ECR, define la etiqueta (hash corto del commit) e inicia sesión en ECR |
| `build` | Corre `pytest`; si una prueba falla, la fase se detiene y no se construye la imagen. Si pasan, `docker build` con las etiquetas `<hash>` y `latest` |
| `post_build` | Solo si todo pasó: `docker push` de las dos etiquetas y genera `imageDetail.json` |

Salidas:

- **Imagen** en ECR: `477139660273.dkr.ecr.us-east-2.amazonaws.com/blacklist-service:<hash>` (y `latest`).
- **Informe de pruebas** en CodeBuild (grupo `blacklist-service-ecs-build-pytest-reports`).
- **Artefacto** en S3 (`blacklist-service-ec/BuildArtif/`) con `imageDetail.json`, `appspec.yaml` y `taskdef.json`, las entradas de la etapa de despliegue con CodeDeploy.

El proyecto de CodeBuild (`blacklist-service-ecs-build`) corre en modo **privilegiado** (necesario para Docker) y su rol tiene permiso para subir imágenes solo al repositorio `blacklist-service` de ECR.

### Pipeline de la entrega 2 (`blacklist-service-ci`)

Instala dependencias, ejecuta `pytest`, publica el informe de pruebas y arma un `.zip` con los mismos archivos del despliegue manual en Beanstalk. Si una prueba falla, no se genera el artefacto. El `.zip` queda en `blacklist-service-ci/BuildArtif/`, con nombre aleatorio y sin extensión; se revisa con `unzip -l <archivo>`.

## Despliegue en ECS Fargate

```
Internet → (80) ALB blacklist-alb → (8000) tarea Fargate → (5432) RDS PostgreSQL
```

| Recurso | Nombre |
|---|---|
| Repositorio ECR | `blacklist-service` |
| Cluster / servicio | `blacklist-cluster` / `blacklist-svc` (1 tarea, controlador de despliegue `CODE_DEPLOY`) |
| Task definition | `blacklist-task` (Fargate, 0.25 vCPU / 0.5 GB, contenedor `blacklist-service` en el puerto 8000) |
| Load balancer | `blacklist-alb`, agente HTTP:80 |
| Target groups | `blacklist-tg-blue` (en uso) y `blacklist-tg-green` (para blue/green), health check en `/ping` |
| Secretos | Parameter Store: `/blacklist/DATABASE_URL` y `/blacklist/JWT_SECRET_KEY` (SecureString) |
| Rol de ejecución | `ecsTaskExecutionRole`, con permiso para leer solo `/blacklist/*` |
| Logs | CloudWatch, grupo `/ecs/blacklist-service` (retención de 1 semana) |

Seguridad de red:

- `blacklist-alb-sg`: entrada 80 desde internet.
- `blacklist-tasks-sg`: entrada 8000 solo desde `blacklist-alb-sg`.
- `blacklist-db-sg` (RDS): entrada 5432 desde `blacklist-tasks-sg` (y desde las instancias de Beanstalk).

La tarea recibe `DATABASE_URL` y `JWT_SECRET_KEY` como `secrets` con `valueFrom`: ECS las lee de Parameter Store al arrancar, así que la task definition solo contiene los ARN de los parámetros, nunca los valores.

### Archivos para el despliegue continuo

| Archivo | Para qué sirve |
|---|---|
| `taskdef.json` | Task definition de la app. La imagen es el marcador `<IMAGE1_NAME>`, que el pipeline reemplaza por la imagen recién construida |
| `appspec.yaml` | Instrucciones para CodeDeploy: usa `<TASK_DEFINITION>` (la revisión nueva) y conecta el contenedor `blacklist-service` en el puerto 8000 al load balancer |
| `imageDetail.json` | Lo genera el build con la dirección de la imagen publicada |

### Publicar una imagen a mano

Requiere la AWS CLI configurada (`aws login`) con la región `us-east-2`:

```bash
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 477139660273.dkr.ecr.us-east-2.amazonaws.com
docker build -t blacklist-service .
docker tag blacklist-service:latest 477139660273.dkr.ecr.us-east-2.amazonaws.com/blacklist-service:latest
docker push 477139660273.dkr.ecr.us-east-2.amazonaws.com/blacklist-service:latest
```

## Despliegue en Elastic Beanstalk (entregas 1 y 2)

Generar el paquete desde la raíz del repo:

```bash
zip -r deploy.zip application.py Procfile requirements.txt VERSION app -x "*__pycache__*"
```

El `.zip` incluye solo el código necesario, con los archivos en la raíz. No incluye `venv/`, `.git/`, `.env`, `postman/` ni `docker-compose.yml`.

Configuración del ambiente:

- Plataforma: **Python 3.13 en Amazon Linux 2023**.
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
├── application.py       # Punto de entrada para Gunicorn
├── Dockerfile           # Imagen de la app para ECS Fargate
├── .dockerignore        # Lo que no entra a la imagen (.env, pruebas, Postman…)
├── buildspec-ecs.yml    # Build del pipeline de contenedores (pruebas + imagen en ECR)
├── taskdef.json         # Task definition para el despliegue en Fargate
├── appspec.yaml         # Instrucciones para CodeDeploy (blue/green)
├── buildspec.yml        # Build del pipeline de la entrega 2 (.zip para Beanstalk)
├── Procfile             # Arranque en Beanstalk
├── generate_token.py    # Genera el token JWT estático
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

Tipos: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `build`, `ci`. Ejemplo: `feat(api): agrega endpoint POST /blacklists`.

Flujo de trabajo: ramas `feature/...` y Pull Request hacia `main` con al menos una aprobación.
