FROM python:3.11-slim

# Install system dependencies for OpenSMILE
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8011

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]