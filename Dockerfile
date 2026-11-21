FROM public.ecr.aws/docker/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEW_RELIC_APP_NAME=blacklist-service \
    NEW_RELIC_LOG=stdout \
    NEW_RELIC_LOG_LEVEL=info \
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY application.py VERSION ./
COPY app/ app/
RUN chmod -R a+rX /app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# newrelic-admin carga el agente de New Relic antes que la app (sin llave, la app corre igual y el agente no reporta)
ENTRYPOINT ["newrelic-admin", "run-program"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "application:application"]
