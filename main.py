import json, logging, os, re, subprocess, tempfile
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_file
from werkzeug.utils import secure_filename

app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=250*1024*1024
logging.basicConfig(level=logging.INFO)
log=logging.getLogger("klebee")

PAGE="""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Super Robô Klebee</title>
<style>
:root{color-scheme:dark;--o:#ff6b18;--bg:#111214;--p:#1d1f23;--line:#383b42;--muted:#b8bbc3}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#392316,transparent 45%),var(--bg);color:#fff;font:16px/1.45 system-ui,Arial,sans-serif}main{max-width:900px;margin:auto;padding:28px 18px 60px}.brand{color:var(--o);font-weight:900;letter-spacing:.14em;font-size:13px}h1{font-size:clamp(32px,6vw,50px);line-height:1.02;margin:12px 0}p,.hint,.foot{color:var(--muted)}.panel{background:var(--p);border:1px solid var(--line);border-radius:18px;padding:22px;margin-top:22px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field{display:flex;flex-direction:column;gap:7px;margin-bottom:15px}label{font-weight:750;font-size:14px}input,textarea,select{width:100%;background:#111214;color:#fff;border:1px solid #454952;border-radius:10px;padding:12px;font:inherit}textarea{min-height:110px}button{background:var(--o);border:0;border-radius:12px;color:#17100b;font-weight:900;font-size:16px;padding:16px;width:100%;cursor:pointer}button:disabled{opacity:.55}.hint,.foot{font-size:12px}.status{white-space:pre-wrap;color:#ffd0b5;margin-top:14px}@media(max-width:640px){.grid{grid-template-columns:1fr}.panel{padding:16px}}
</style></head><body><main><div class="brand">KLEBEE • ESTÚDIO DE VÍDEOS</div><h1>Vídeos de produto.<br><span style="color:var(--o)">Prontos para publicar.</span></h1><p>Envie um vídeo real do produto e gere uma versão vertical com voz brasileira, legendas grandes, chamada comercial e áudio mixado.</p>
<form id="f" class="panel"><div class="field"><label>1. Vídeo original do produto *</label><input name="video" type="file" accept="video/mp4,video/quicktime,video/webm" required><div class="hint">É necessário enviar um arquivo de vídeo, não apenas a página do produto na Shopee.</div></div>
<div class="grid"><div class="field"><label>Chamada principal</label><input name="headline" maxlength="60" value="OLHA ESSE ACHADINHO!"></div><div class="field"><label>Chamada final</label><input name="cta" maxlength="40" value="VEJA NA SHOPEE"></div></div>
<div class="field"><label>2. Narração em português brasileiro *</label><textarea name="script" maxlength="1800" required>Calor na mesa de trabalho? Olha essa opção compacta! Um mini climatizador USB para deixar por perto no dia a dia. Confira o produto e o preço na Shopee!</textarea><div class="hint">Use apenas características e promessas confirmadas pelo anúncio.</div></div>
<div class="grid"><div class="field"><label>Voz</label><select name="voice"><option value="pt-BR-FranciscaNeural">Francisca — feminina brasileira</option><option value="pt-BR-AntonioNeural">Antônio — masculina brasileira</option></select></div><div class="field"><label>Música de fundo (opcional)</label><input name="music" type="file" accept="audio/*"><div class="hint">Envie apenas música que tenha direito de utilizar.</div></div></div>
<button id="b">GERAR VÍDEO FINAL</button><div class="status" id="s" role="status"></div><div class="foot">O arquivo só é entregue depois da validação técnica do MP4. Assista antes de publicar.</div></form></main>
<script>const f=document.querySelector('#f'),b=document.querySelector('#b'),s=document.querySelector('#s');f.onsubmit=async e=>{e.preventDefault();b.disabled=true;b.textContent='RENDERIZANDO…';s.textContent='Gerando voz, legendas e composição vertical…';try{let r=await fetch('/api/render',{method:'POST',body:new FormData(f)}),t=r.headers.get('content-type')||'';if(!r.ok){let d=t.includes('json')?await r.json():{error:await r.text()};throw Error(d.error||d.detail||'Falha na renderização')}let u=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=u;a.download='super_robo_klebee.mp4';a.click();URL.revokeObjectURL(u);s.textContent='MP4 gerado e enviado para download. Confira o vídeo inteiro antes de publicar.'}catch(x){s.textContent='Falha: '+x.message}finally{b.disabled=false;b.textContent='GERAR VÍDEO FINAL'}};</script></body></html>"""

def run(cmd, timeout=360):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or "Falha de mídia")[-2500:])
    return p.stdout.strip()

def probe(path):
    d=json.loads(run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type","-of","json",str(path)]))
    return float(d.get("format",{}).get("duration") or 0),d.get("streams",[])

def clean(s,n):
    return re.sub(r"\s+"," ",re.sub(r"[\x00-\x1f]"," ",s or "")).strip()[:n]

def stamp(sec):
    ms=max(0,int(sec*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text,duration,path):
    phrases=[x.strip() for x in re.split(r"(?<=[.!?])\s+",text) if x.strip()]
    chunks=[]
    for phrase in phrases:
        words=phrase.split()
        while len(words)>8: chunks.append(" ".join(words[:8])); words=words[8:]
        if words: chunks.append(" ".join(words))
    if not chunks: chunks=[text]
    weights=[max(1,len(x)) for x in chunks]; total=sum(weights); start=0; rows=[]
    for i,(chunk,w) in enumerate(zip(chunks,weights),1):
        end=duration if i==len(chunks) else start+duration*w/total
        rows.append(f"{i}\n{stamp(start)} --> {stamp(end)}\n{chunk}\n"); start=end
    Path(path).write_text("\n".join(rows),encoding="utf-8")

def esc(s):
    return s.replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace("%","\\%").replace(",","\\,")

@app.get("/")
def home(): return render_template_string(PAGE)

@app.get("/health")
def health(): return jsonify(status="online",app="Super Robô Klebee",engine="novo-motor-audiovisual-v1")

@app.post("/api/render")
def render():
    upload=request.files.get("video")
    if not upload or not upload.filename: return jsonify(error="Envie o vídeo original do produto."),400
    ext=Path(secure_filename(upload.filename)).suffix.lower()
    if ext not in {".mp4",".mov",".m4v",".webm"}: return jsonify(error="Formato não suportado. Use MP4, MOV ou WebM."),400
    script=clean(request.form.get("script"),1800)
    if len(script.split())<5: return jsonify(error="A narração precisa ter pelo menos cinco palavras."),400
    headline=esc(clean(request.form.get("headline","ACHADINHO IMPERDÍVEL"),60))
    cta=esc(clean(request.form.get("cta","VEJA NA SHOPEE"),40))
    voice=request.form.get("voice","pt-BR-FranciscaNeural")
    if voice not in {"pt-BR-FranciscaNeural","pt-BR-AntonioNeural"}: voice="pt-BR-FranciscaNeural"
    music=request.files.get("music")
    mext=Path(secure_filename(music.filename)).suffix.lower() if music and music.filename else ""
    if mext and mext not in {".mp3",".wav",".m4a",".aac",".ogg"}: return jsonify(error="Formato de música não suportado."),400
    with tempfile.TemporaryDirectory(prefix="klebee-") as td:
        td=Path(td); src=td/("source"+ext); tts=td/"voice.mp3"; out=td/"super_robo_klebee.mp4"; src_upload=upload
        src_upload.save(src); music_path=None
        if music and music.filename: music_path=td/("music"+mext); music.save(music_path)
        try:
            run(["edge-tts","--voice",voice,"--text",script,"--write-media",str(tts)],timeout=120)
            srcdur,streams=probe(src)
            if srcdur<1 or not any(x.get("codec_type")=="video" for x in streams): raise ValueError("O arquivo não contém vídeo válido.")
        except Exception as e:
            log.exception("Falha no preparo")
            return jsonify(error="Não foi possível preparar o vídeo.",detail=str(e)[-1600:]),500
        try:
            vdur,_=probe(tts); duration=min(15.0,srcdur,max(1.0,vdur+0.5))
            srt=td/"captions.srt"; make_srt(script,duration,srt)
            font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            vf=("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
                "drawbox=x=42:y=85:w=996:h=185:color=black@0.62:t=fill,"
                f"drawtext=fontfile={font}:text='{headline}':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=145:borderw=2:bordercolor=black,"
                f"subtitles='{srt}':force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=250,"
                "WrapStyle=2',"
                "drawbox=x=120:y=1600:w=840:h=125:color=0xFF6B18@0.97:t=fill,"
                f"drawtext=fontfile={font}:text='{cta}':fontcolor=black:fontsize=44:x=(w-text_w)/2:y=1638")
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(src),"-i",str(tts)]
            if music_path: cmd += ["-stream_loop","-1","-i",str(music_path)]
            cmd += ["-vf",vf,"-t",f"{duration:.3f}","-map","0:v:0","-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p"]
            aud=[]
            if any(x.get("codec_type")=="audio" for x in streams): aud.append("[0:a:0]volume=0.12[orig]")
            aud.append("[1:a:0]volume=1.0[voice]")
            if music_path: aud.append("[2:a:0]volume=0.10[music]")
            labels=(["[orig]"] if any(x.get("codec_type")=="audio" for x in streams) else [])+["[voice]"]+(["[music]"] if music_path else [])
            aud.append("".join(labels)+f"amix=inputs={len(labels)}:duration=longest:dropout_transition=2,alimiter=limit=0.95[aout]")
            cmd += ["-filter_complex",";".join(aud),"-map","[aout]","-c:a","aac","-b:a","160k","-movflags","+faststart",str(out)]
            run(cmd,timeout=420)
            finaldur,finalstreams=probe(out)
            if not out.exists() or out.stat().st_size<50000: raise RuntimeError("O arquivo final está ausente ou pequeno demais.")
            if not any(x.get("codec_type")=="video" for x in finalstreams) or not any(x.get("codec_type")=="audio" for x in finalstreams): raise RuntimeError("O MP4 final não contém vídeo e áudio válidos.")
            if finaldur<1 or finaldur>15.5: raise RuntimeError(f"Duração fora do esperado: {finaldur:.1f}s")
            return send_file(out,mimetype="video/mp4",as_attachment=True,download_name="super_robo_klebee.mp4")
        except Exception as e:
            log.exception("Falha na renderização")
            return jsonify(error="A renderização falhou; o vídeo não foi marcado como concluído.",detail=str(e)[-2000:]),500

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")))
