import React from "react";
import { AbsoluteFill, Audio, Composition, Sequence, Video, registerRoot, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { createTikTokStyleCaptions } from "@remotion/captions";
type Cue = {text:string;startMs:number;endMs:number};
type Props = {videoPath:string;narrationPath:string;headline:string;captionSegments:Cue[]};
const Headline:React.FC<{text:string}> = ({text}) => {
 const frame=useCurrentFrame(); const {fps}=useVideoConfig();
 return <AbsoluteFill style={{alignItems:"center",justifyContent:"flex-start",paddingTop:145,pointerEvents:"none"}}><div style={{maxWidth:"90%",display:"flex",flexWrap:"wrap",justifyContent:"center"}}>{Array.from(text).map((c,i)=>{
  const p=spring({frame:frame-Math.round(i*0.032*fps),fps,config:{damping:10,stiffness:240,mass:0.65}});
  if(c===" ") return <span key={i} style={{width:20}}/>;
  return <span key={i} style={{fontFamily:"Arial Black,Arial,sans-serif",fontSize:76,fontWeight:900,color:"#FF6A00",WebkitTextStroke:"3px white",textShadow:"0 7px 0 #7D2E00,0 12px 22px #0009",transform:"translateY("+(1-p)*95+"px) rotate("+(1-p)*(i%2?16:-16)+"deg) scale("+(0.45+0.55*p)+")",opacity:p,lineHeight:1.02}}>{c}</span>;
 })}</div></AbsoluteFill>;
};
const Karaoke:React.FC<{segments:Cue[]}> = ({segments}) => {
 const frame=useCurrentFrame(); const {fps}=useVideoConfig(); const now=frame/fps*1000;
 if(!segments.length) return null;
 const {pages}=createTikTokStyleCaptions({captions:segments as any,combineTokensWithinMilliseconds:350});
 const line=(pages as any[]).find(p=>now>=p.startMs&&now<p.startMs+(p.durationMs??Infinity)); if(!line) return null;
 return <AbsoluteFill style={{justifyContent:"flex-end",alignItems:"center",padding:"0 54px 290px",pointerEvents:"none"}}><div style={{maxWidth:"92%",textAlign:"center",fontFamily:"Arial Black,Arial,sans-serif",fontSize:55,fontWeight:900,lineHeight:1.16,textTransform:"uppercase"}}>{line.tokens.map((t:any,i:number)=>{
 const active=now>=(t.fromMs??0)&&now<(t.toMs??Infinity);
 return <span key={i} style={{display:"inline-block",margin:"0 5px 7px",color:active?"#FFE600":"#FFFFFF",WebkitTextStroke:"1.5px #101010",textShadow:active?"0 0 18px #ffe600b3,0 5px 0 #000":"0 5px 0 #000,0 8px 16px #000c",transform:active?"scale(1.16)":"scale(1)"}}>{t.text}</span>;
 })}</div></AbsoluteFill>;
};
const Klebee:React.FC<Props> = ({videoPath,narrationPath,headline,captionSegments}) => {
 const {durationInFrames}=useVideoConfig();
 return <AbsoluteFill style={{backgroundColor:"#000"}}><Video src={videoPath} style={{width:"100%",height:"100%",objectFit:"cover"}} volume={0.16}/><Audio src={narrationPath} volume={1}/><Sequence from={0} durationInFrames={Math.min(durationInFrames,96)}><Headline text={headline}/></Sequence><Karaoke segments={captionSegments}/></AbsoluteFill>;
};
const Root:React.FC=()=> <Composition id="KlebeeVideo" component={Klebee} durationInFrames={450} fps={30} width={1080} height={1920} defaultProps={{videoPath:"/tmp/klebee-input.mp4",narrationPath:"/tmp/klebee-voice.mp3",headline:"OLHA ESSE ACHADINHO!",captionSegments:[]}}/>;
registerRoot(Root);
