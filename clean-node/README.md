# Super Robô Klebee — Node.js clean core (experimental)

This directory is an isolated rebuild. It does not replace the existing app or trigger a Railway deployment.

## Run locally / in container
- Requires Node.js 20+, FFmpeg with libass/subtitles and drawtext, Python 3 and `edge-tts`.
- `npm install`
- `npm run check`
- `npm start`
- Health check: `GET /health`
- Upload: `POST /api/jobs` as multipart form. Required: `video` (MP4). Optional: `music` (MP3/WAV/M4A/AAC/OGG), `headline`, `detail`, `cta`, `narration`.
- Poll `GET /api/jobs/:id`; completed output at `GET /api/jobs/:id/video`.

When music is provided, it loops to cover the clip and is ducked automatically while the voiceover is present. Original video audio is mixed quietly under narration.

## Scope / known gaps
- Experimental scaffold, not production-ready.
- Job state is in memory; restarting the process loses status. Files under /tmp are ephemeral.
- Captions use estimated timing based on total voice duration, not forced alignment; precise speech-to-text alignment remains a milestone.
- No default music library, retries, persistent storage, authentication, cleanup or durable queue yet.
- Output is limited to 15 seconds and letterboxed to 9:16 to preserve the full product frame.
- Do not point production Railway at this directory until CI passes, a real uploaded clip is rendered and inspected, and deployment is explicitly approved.
