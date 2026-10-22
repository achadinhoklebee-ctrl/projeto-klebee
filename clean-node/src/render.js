import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export async function renderVideo(job) {
  const output = path.join(job.dir, 'final.mp4');
  const probe = await execFileAsync('ffprobe', [
    '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=index',
    '-of', 'csv=p=0', job.input
  ]);
  const hasSourceAudio = Boolean(probe.stdout.trim());
  const subtitlePath = job.srt
    .replaceAll('\\\\', '/')
    .replaceAll(':', '\\:')
    .replaceAll("'", "\\'");
  const videoFilter = [
    'scale=1080:1920:force_original_aspect_ratio=decrease',
    'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
    'setsar=1',
    `drawtext=text='${escapeText(job.headline)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=54:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=120:enable='lt(t,4)'`,
    `drawtext=text='${escapeText(job.detail)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=42:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=220:enable='between(t,4,8)'`,
    `subtitles='${subtitlePath}':force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=150'`
  ].join(',');

  const args = ['-y', '-i', job.input, '-i', job.audio, '-t', String(job.duration),
    '-vf', videoFilter];

  if (hasSourceAudio) {
    args.push('-filter_complex',
      '[0:a:0]volume=0.16[original];[1:a:0]volume=1.0[voice];[original][voice]amix=inputs=2:duration=first:dropout_transition=1[aout]',
      '-map', '0:v:0', '-map', '[aout]');
  } else {
    args.push('-map', '0:v:0', '-map', '1:a:0');
  }

  args.push('-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
    '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', output);
  await execFileAsync('ffmpeg', args, { timeout: 240000, maxBuffer: 4 * 1024 * 1024 });
  return output;
}

function escapeText(value) {
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/:/g, '\\:')
    .replace(/'/g, "\\'")
    .replace(/%/g, '\\%')
    .replace(/,/g, '\\,')
    .replace(/\[/g, '\\[')
    .replace(/\]/g, '\\]');
}
