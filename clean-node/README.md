# Super Robô Klebee — Node.js clean core (experimental)

This directory is an isolated rebuild scaffold. It does not replace the existing app or trigger a Railway deployment.

## Run locally / in container
- Requires Node.js 20+, FFmpeg with libass/subtitles and drawtext, Python 3 and `edge-tts`.
- `npm install`
- `npm run check`
- `npm start`
- Health check: `GET /health`
- Upload: `POST /api/jobs`, multipart field `video` (MP4); optional fields `headline`, `detail`, `cta`, `narration`.
- Poll `GET /api/jobs/:id`; completed output at `GET /api/jobs/:id/video`.

## Scope / known gaps
- This is a first isolated pipeline skeleton, not production-ready.
- Job state is in memory; restarting the process loses status. Files under /tmp are ephemeral.
- Captions use estimated word timing, not forced alignment. Real word-level sync is a required next milestone.
- Original audio is mixed quietly under narration; music upload/selection, retries, persistent storage, authentication, cleanup and robust job queue are not implemented yet.
- It currently renders up to 15 seconds and letterboxes to 9:16 to preserve the entire product frame. Verify output on a real uploaded clip before deployment.
- Do not point production Railway at this directory until local/CI end-to-end video validation and explicit approval.