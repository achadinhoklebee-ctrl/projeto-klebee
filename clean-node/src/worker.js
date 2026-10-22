import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { renderVideo } from './render.js';

const execFileAsync = promisify(execFile);

export async function runJob(job) {
  const probe = await execFileAsync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', job.input
  ]);
  const sourceDuration = Number(probe.stdout.trim());
  if (!Number.isFinite(sourceDuration) || sourceDuration < 0.5) {
    throw new Error('O arquivo enviado não parece ser um vídeo válido.');
  }

  const duration = Math.min(15, sourceDuration);
  const narration = job.narration.trim() || `${job.headline}. ${job.detail}. ${job.cta}.`;
  const audio = path.join(job.dir, 'voice.mp3');
  const srt = path.join(job.dir, 'captions.srt');
  await fs.writeFile(path.join(job.dir, 'narration.txt'), narration, 'utf8');

  await execFileAsync('edge-tts', [
    '--voice', 'pt-BR-FranciscaNeural', '--text', narration, '--write-media', audio
  ], { timeout: 90000 });

  const audioProbe = await execFileAsync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', audio
  ]);
  const voiceDuration = Number(audioProbe.stdout.trim());
  if (!Number.isFinite(voiceDuration) || voiceDuration <= 0) {
    throw new Error('Não foi possível validar a duração da narração gerada.');
  }

  const words = narration.trim().split(/\s+/u).filter(Boolean);
  const chunkSize = 5;
  const lines = [];
  for (let i = 0; i < words.length; i += chunkSize) {
    const start = voiceDuration * i / words.length;
    const end = voiceDuration * Math.min(i + chunkSize, words.length) / words.length;
    if (start >= duration) break;
    const cueEnd = Math.min(duration, Math.max(start + 0.25, end));
    lines.push(
      String(lines.length / 4 + 1),
      `${stamp(start)} --> ${stamp(cueEnd)}`,
      words.slice(i, i + chunkSize).join(' '),
      ''
    );
  }
  if (lines.length === 0) throw new Error('Não foi possível criar as legendas.');
  await fs.writeFile(srt, lines.join('\n') + '\n', 'utf8');

  await renderVideo({ ...job, audio, srt, duration });
  const finalProbe = await execFileAsync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height',
    '-of', 'json', path.join(job.dir, 'final.mp4')
  ]);
  const verification = JSON.parse(finalProbe.stdout);
  const video = verification.streams?.find((stream) => stream.codec_type === 'video');
  const audioStream = verification.streams?.find((stream) => stream.codec_type === 'audio');
  if (!video || video.width !== 1080 || video.height !== 1920 || !audioStream) {
    throw new Error('A validação do MP4 final falhou: vídeo vertical 1080x1920 e áudio são obrigatórios.');
  }
  return {
    sourceDurationSeconds: sourceDuration,
    outputDurationSeconds: Number(verification.format?.duration || duration),
    verification,
    narration,
    captionsFile: 'captions.srt',
    musicUsed: Boolean(job.music)
  };
}

function stamp(seconds) {
  const ms = Math.max(0, Math.round(seconds * 1000));
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const milli = ms % 1000;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(milli).padStart(3, '0')}`;
}
