import fs from "node:fs";
import path from "node:path";
import { bundle } from "@remotion/bundler";
import { getCompositions, renderMedia } from "@remotion/renderer";
const args=process.argv.slice(2);
const videoPath=args[0], narrationPath=args[1], captionsPath=args[2], outputPath=args[3], headline=args[4]||"OLHA ESSE ACHADINHO!";
if(!videoPath||!narrationPath||!captionsPath||!outputPath){console.error("Uso: npm run render:klebee -- video.mp4 voz.mp3 captions.json saida.mp4 \"HEADLINE\"");process.exit(2);}
for(const f of [videoPath,narrationPath,captionsPath]) if(!fs.existsSync(f)) throw new Error("Arquivo não encontrado: "+f);
const captionSegments=JSON.parse(fs.readFileSync(captionsPath,"utf8"));
if(!Array.isArray(captionSegments)||captionSegments.some(x=>typeof x.text!=="string"||!Number.isFinite(x.startMs)||!Number.isFinite(x.endMs)||x.endMs<=x.startMs)) throw new Error("captions.json deve conter palavras com text/startMs/endMs válidos.");
const serveUrl=await bundle({entryPoint:path.resolve("remotion/index.tsx")});
const inputProps={videoPath:path.resolve(videoPath),narrationPath:path.resolve(narrationPath),headline,captionSegments};
const comps=await getCompositions(serveUrl,{inputProps});
const comp=comps.find(x=>x.id==="KlebeeVideo"); if(!comp) throw new Error("Composição KlebeeVideo não encontrada.");
const durationInFrames=Math.min(comp.durationInFrames,450);
await renderMedia({composition:{...comp,durationInFrames},serveUrl,codec:"h264",outputLocation:path.resolve(outputPath),inputProps,pixelFormat:"yuv420p",onProgress:({progress})=>process.stdout.write("Render "+Math.round(progress*100)+"%\r")});
console.log("\nMP4 gerado em "+path.resolve(outputPath));
