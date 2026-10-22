import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export async function renderVideo(job) {
  const output = path.join(job.dir, 'final.mp4');
  const audioProbe = await execFileAsync('ffprobe', [
    '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=index',
    '-of', 'csv=p=0', job.input
  ]);
  const hasSourceAudio = Boolean(audioProbe.stdout.trim());
  const hasMusic = Boolean(job.music);
  const subtitlePath = job.srt.replaceAll('\\\\', '/').replaceAll(':', '\\:').replaceAll("'", "\\'");
  const videoFilter = [
    'scale=1080:1920:force_original_aspect_ratio=decrease',
    'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
    'setsar=1',
    `drawtext=text='${escapeText(job.headline)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=76:fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y='120+18*(1-min(t/0.35,1))':alpha='if(lt(t,0.35),t/0.35,1)':enable='lt(t,4)'`,
    `drawtext=text='${escapeText(job.detail)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=58:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y='230+14*(1-min((t-4)/0.35,1))':alpha='if(lt(t-4,0.35),(t-4)/0.35,1)':enable='between(t,4,8)'`,
    `subtitles='${subtitlePath}':force_style='FontName=DejaVu Sans,FontSize=32,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=190'`
  ].join(',');

  const args = ['-y', '-i', job.input, '-i', job.audio];
  if (hasMusic) args.push('-stream_loop', '-1', '-i', job.music);
  args.push('-t', String(job.duration), '-vf', videoFilter);

  const filters = ['[1:a:0]volume=1.0[voice]'];
  if (hasMusic) {
    filters.push('[2:a:0]volume=0.22[musicin]');
    filters.push('[musicin][voice]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=450[musicduck]');
  }
  if (hasSourceAudio) filters.push('[0:a:0]volume=0.12[original]');
  const mixInputs = [];
  if (hasSourceAudio) mixInputs.push('[original]');
  mixInputs.push('[voice]');
  if (hasMusic) mixInputs.push('[musicduck]');
  filters.push(`${mixInputs.join('')}amix=inputs=${mixInputs.length}:duration=first:dropout_transition=1[aout]`);

  args.push('-filter_complex', filters.join(';'), '-map', '0:v:0', '-map', '[aout]',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
    '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', output);
  await execFileAsync('ffmpeg', args, { timeout: 240000, maxBuffer: 4 * 1024 * 1024 });
  return output;
}

function escapeText(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/:/g, '\\:')
    .replace(/'/g, "\\'").replace(/%/g, '\\%').replace(/,/g, '\\,')
    .replace(/\[/g, '\\[').replace(/\]/g, '\\]');
}
