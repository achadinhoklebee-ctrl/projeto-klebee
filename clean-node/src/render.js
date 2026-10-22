import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const execFileAsync = promisify(execFile);

export async function renderVideo(job) {
  const output = path.join(job.dir, 'final.mp4');
  const subtitles = job.srt.replaceAll('\\', '/').replaceAll(':', '\\:').replaceAll("'", "\\'");
  const filter = [
    'scale=1080:1920:force_original_aspect_ratio=decrease',
    'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
    'setsar=1',
    `drawtext=text='${escapeText(job.headline)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=54:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=120:enable='lt(t,4)'`,
    `drawtext=text='${escapeText(job.detail)}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=42:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=220:enable='between(t,4,8)'`,
    `subtitles='${subtitles}':force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=150'`
  ].join(',');
  const args = ['-y','-i',job.input,'-i',job.audio,'-t',String(job.duration),'-vf',filter,'-filter_complex','[1:a]volume=1.0[voice];[0:a]volume=0.16[original];[original][voice]amix=inputs=2:duration=first:dropout_transition=1[aout]','-map','0:v:0','-map','[aout]','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','160k','-movflags','+faststart',output];
  try {
    await execFileAsync('ffmpeg', args, { timeout: 240000, maxBuffer: 4*1024*1024 });
  } catch (error) {
    // Some uploaded videos have no audio stream; render voice-only in that case.
    if (!String(error.stderr || '').includes('matches no streams') && !String(error.stderr || '').includes('Stream specifier')) throw error;
    const noSourceAudio = args.filter((v,i) => !(v === '[0:a]volume=0.16[original]' || v === '[original][voice]amix=inputs=2:duration=first:dropout_transition=1[aout]'));
    const at = noSourceAudio.indexOf('-filter_complex');
    noSourceAudio.splice(at, 2, '-map','1:a:0');
    await execFileAsync('ffmpeg', noSourceAudio, { timeout: 240000, maxBuffer: 4*1024*1024 });
  }
  return output;
}
function escapeText(value) { return String(value).replace(/\\/g,'\\\\').replace(/:/g,'\\:').replace(/'/g,"\\'").replace(/%/g,'\\%').replace(/,/g,'\\,').replace(/\[/g,'\\[').replace(/\]/g,'\\]'); }