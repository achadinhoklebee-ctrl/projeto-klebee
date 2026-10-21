FROM python:3.10-slim

# Instala o FFmpeg e dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia os ficheiros do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Executa o Gunicorn através do Python para garantir o arranque correto
CMD ["python3", "-m", "gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "--timeout", "120"]
