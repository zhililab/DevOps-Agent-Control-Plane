FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

WORKDIR /app/backend

COPY backend/pyproject.toml ./
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation --retries 8 --default-timeout 120 .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
