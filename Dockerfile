FROM python:3.10-slim

# Dependências de sistema necessárias ao áudio/vídeo e ao renderizador Remotion.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    chromium \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium
ENV NODE_OPTIONS=--max-old-space-size=1536

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json .
RUN npm install --no-audit --no-fund

COPY . .

CMD ["python3", "-m", "gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "--timeout", "900"]
