FROM node:20-bookworm-slim
ENV NODE_ENV=production PORT=8080
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg python3 python3-pip fonts-dejavu-core && rm -rf /var/lib/apt/lists/* && python3 -m pip install --break-system-packages edge-tts
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY src ./src
RUN mkdir -p /tmp/klebee/jobs
EXPOSE 8080
CMD ["npm","start"]