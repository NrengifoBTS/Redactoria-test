# Build stage
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/

# Expose the port FastAPI runs on
EXPOSE 8080

# Aplica migraciones pendientes y luego arranca la API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8080"]