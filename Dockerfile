FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_fastapi.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_fastapi.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p /app/templates /app/static/css /app/static/js

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
