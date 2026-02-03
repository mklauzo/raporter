FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY raport_servera.sh .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV FLASK_APP=app

EXPOSE 5000

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
