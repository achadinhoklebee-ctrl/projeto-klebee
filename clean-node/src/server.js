import express from 'express';
import multer from 'multer';
import { nanoid } from 'nanoid';
import fs from 'node:fs/promises';
import path from 'node:path';
import { runJob } from './worker.js';

const app = express();
const PORT = Number(process.env.PORT || 8080);
const ROOT = process.env.KLEBEE_WORK_DIR || '/tmp/klebee/jobs';
await fs.mkdir(ROOT, { recursive: true });
const upload = multer({
  dest: path.join(ROOT, 'uploads'),
  limits: { fileSize: 250 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => cb(null, file.mimetype === 'video/mp4' || /\.mp4$/i.test(file.originalname))
});
const jobs = new Map();

app.get('/health', (_req, res) => res.json({ ok: true, service: 'super-robo-klebee-node', mode: 'isolated-rebuild' }));
app.post('/api/jobs', upload.single('video'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'Envie um arquivo MP4 no campo video.' });
  const id = nanoid(12);
  const dir = path.join(ROOT, id);
  await fs.mkdir(dir, { recursive: true });
  const input = path.join(dir, 'input.mp4');
  await fs.rename(req.file.path, input);
  const config = {
    id, dir, input,
    headline: String(req.body.headline || 'Olha essa novidade!').slice(0, 90),
    detail: String(req.body.detail || 'Praticidade para o seu dia a dia').slice(0, 120),
    narration: String(req.body.narration || '').slice(0, 1200),
    cta: String(req.body.cta || 'Confira na Shopee').slice(0, 90)
  };
  jobs.set(id, { id, status: 'queued', createdAt: new Date().toISOString() });
  res.status(202).json({ id, status: 'queued', statusUrl: `/api/jobs/${id}` });
  setImmediate(async () => {
    jobs.set(id, { ...jobs.get(id), status: 'processing' });
    try {
      const result = await runJob(config);
      jobs.set(id, { ...jobs.get(id), status: 'completed', output: `/api/jobs/${id}/video`, report: result });
    } catch (e) {
      jobs.set(id, { ...jobs.get(id), status: 'failed', error: String(e?.message || e).slice(0, 1000) });
      console.error('[job failed]', id, e);
    }
  });
});
app.get('/api/jobs/:id', (req, res) => {
  const job = jobs.get(req.params.id);
  return job ? res.json(job) : res.status(404).json({ error: 'Trabalho não encontrado neste processo.' });
});
app.get('/api/jobs/:id/video', async (req, res) => {
  const job = jobs.get(req.params.id);
  if (!job || job.status !== 'completed') return res.status(409).json({ error: 'Vídeo ainda não está pronto.' });
  res.type('mp4').sendFile(path.join(ROOT, req.params.id, 'final.mp4'));
});
app.listen(PORT, '0.0.0.0', () => console.log(`Super Robô Klebee Node listening on ${PORT}`));