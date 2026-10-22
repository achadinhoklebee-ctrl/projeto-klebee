import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { renderVideo } from './render.js';
const execFileAsync = promisify(execFile);

export async function runJob(job) {
  const probe = await execFileAsync('ffprobe', ['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',job.input]);
  const sourceDuration = Number(probe.stdout.trim());
  if (!Number.isFinite(sourceDuration) || sourceDuration < 0.5) throw new Error('O arquivo enviado não parece ser um vídeo válido.');
  const duration = Math.min(15, sourceDuration);
  const narration = job.narration.trim() || `${job.headline}. ${job.detail}. ${job.cta}.`;
  const audio = path.join(job.dir, 'voice.mp3');
  const srt = path.join(job.dir, 'captions.srt');
  const txt = path.join(job.dir, 'narration.txt');
  await fs.writeFile(txt, narration, 'utf8');
  await execFileAsync('edge-tts', ['--voice','pt-BR-FranciscaNeural','--text',narration,'--write-media',audio], { timeout: 90000 });
  const words = narration.split(/\s+/).filter(Boolean);
  const segment = Math.max(0.45, Math.min(1.15, (duration - 1) / Math.max(words.length, 1)));
  const lines = [];
  for (let i=0;i<words.length;i+=5) {
    const start = i*segment;
    const end = Math.min(duration, (Math.min(i+5,words.length))*segment);
    if (start >= duration) break;
    lines.push(String(lines.length+1), `${stamp(start)} --> ${stamp(Math.max(start+0.2,end))}`, words.slice(i,i+5).join(' '), '');
  }
  await fs.writeFile(srt, lines.join('\n'), 'utf8');
  await renderVideo({ ...job, audio, srt, duration });
  const finalProbe = await execFileAsync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',path.join(job.dir,'final.mp4')]);
  return { sourceDurationSeconds: sourceDuration, outputDurationSeconds: duration, verification: JSON.parse(finalProbe.stdout), narration, captionsFile: 'captions.srt' };
}
function stamp(seconds) {
  const ms = Math.round(seconds*1000), h=Math.floor(ms/3600000), m=Math.floor(ms%3600000/60000), s=Math.floor(ms%60000/1000), milli=ms%1000;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(milli).padStart(3,'0')}`;
}