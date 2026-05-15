FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN sed -i 's|deb.debian.org|ftp.de.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

RUN pip install --user --no-cache-dir \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.org \
    -r requirements.txt

# Final stage
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN sed -i 's|deb.debian.org|ftp.de.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY . .

ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser

EXPOSE 8001

CMD ["uvicorn", "main_fastapi:app", "--host", "0.0.0.0", "--port", "8001"]