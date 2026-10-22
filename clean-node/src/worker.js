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

  const narration = job.narration.trim() || `${job.headline}. ${job.detail}. ${job.cta}.`;
  const audio = path.join(job.dir, 'voice.mp3');
  const srt = path.join(job.dir, 'captions.srt');
  await fs.writeFile(path.join(job.dir, 'narration.txt'), narration, 'utf8');

  // edge-tts writes subtitle timestamps from the speech synthesis stream instead
  // of distributing words uniformly across the total audio duration.
  await execFileAsync('edge-tts', [
    '--voice', 'pt-BR-FranciscaNeural',
    '--text', narration,
    '--write-media', audio,
    '--write-subtitles', srt
  ], { timeout: 90000 });

  const audioProbe = await execFileAsync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', audio
  ]);
  const voiceDuration = Number(audioProbe.stdout.trim());
  if (!Number.isFinite(voiceDuration) || voiceDuration <= 0) {
    throw new Error('Não foi possível validar a duração da narração gerada.');
  }

  // Preserve source length up to the 15-second Shopee target, but never cut the
  // narration mid-sentence. A long narration is rejected with a useful message.
  const duration = Math.min(15, sourceDuration);
  if (voiceDuration > duration + 0.15) {
    throw new Error(`A narração dura ${voiceDuration.toFixed(1)}s, mas o vídeo comporta ${duration.toFixed(1)}s. Encurte o texto para evitar corte de fala.`);
  }

  const subtitleText = await fs.readFile(srt, 'utf8');
  if (!/-->/.test(subtitleText) || !subtitleText.trim()) {
    throw new Error('O Edge TTS não gerou legendas temporizadas; o vídeo não será renderizado com sincronização estimada.');
  }

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
    captionTiming: 'edge-tts subtitle timestamps',
    musicUsed: Boolean(job.music)
  };
}
