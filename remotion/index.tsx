import React from "react";
import { AbsoluteFill, Audio, Composition, Sequence, Video, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { createTikTokStyleCaptions } from "@remotion/captions";

type Cue = { text: string; startMs: number; endMs: number };
type Props = {
  videoPath: string;
  narrationPath: string;
  headline: string;
  middleHeadline: string;
  ctaHeadline: string;
  captionSegments: Cue[];
};

const Kicker: React.FC<{ text: string; variant: "hook" | "benefit" | "cta" }> = ({ text, variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame, fps, config: { damping: 16, stiffness: 140, mass: 0.8 } });
  const accent = variant === "benefit" ? "#FFE45E" : "#FF6A00";
  const y = interpolate(progress, [0, 1], [42, 0]);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: variant === "cta" ? "flex-end" : "flex-start", paddingTop: variant === "cta" ? 0 : 150, paddingBottom: variant === "cta" ? 330 : 0, paddingLeft: 72, paddingRight: 72, pointerEvents: "none" }}>
      <div style={{ maxWidth: "100%", opacity: progress, transform: `translateY(${y}px)`, textAlign: "center" }}>
        <div style={{ display: "inline-block", padding: "18px 24px 20px", borderRadius: 22, background: "rgba(9, 12, 18, 0.78)", border: `2px solid ${accent}`, boxShadow: "0 10px 32px rgba(0,0,0,.32)" }}>
          <div style={{ fontFamily: "Arial Black, Arial, sans-serif", fontSize: 26, fontWeight: 900, letterSpacing: 2.2, color: accent, marginBottom: 8 }}>
            {variant === "hook" ? "OLHA ESSE ACHADINHO" : variant === "benefit" ? "UM DETALHE QUE FAZ DIFERENÇA" : "ENCONTRE NA SHOPEE"}
          </div>
          <div style={{ fontFamily: "Arial Black, Arial, sans-serif", fontSize: 62, fontWeight: 900, lineHeight: 1.03, color: "#FFFFFF", textShadow: "0 3px 0 rgba(0,0,0,.55)", overflowWrap: "anywhere", textWrap: "balance" as any }}>
            {text}
          </div>
          <div style={{ height: 7, width: "62%", margin: "14px auto 0", borderRadius: 8, background: `linear-gradient(90deg, ${accent}, #FFFFFF)` }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Karaoke: React.FC<{ segments: Cue[] }> = ({ segments }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const now = (frame / fps) * 1000;
  if (!segments.length) return null;

  // Remotion expects a leading space on tokens after the first word. Normalize it
  // here so page splitting and wrapping remain predictable even with older JSON.
  const normalized = segments.map((s, i) => ({ ...s, text: i === 0 || /^\s/.test(s.text) ? s.text : " " + s.text }));
  const { pages } = createTikTokStyleCaptions({ captions: normalized as any, combineTokensWithinMilliseconds: 900, breakOnSilenceAfterMilliseconds: 420 });
  const line = (pages as any[]).find((p) => now >= p.startMs && now < p.startMs + (p.durationMs ?? Infinity));
  if (!line) return null;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingLeft: 84, paddingRight: 84, paddingBottom: 245, pointerEvents: "none" }}>
      <div style={{ width: "100%", maxWidth: 900, boxSizing: "border-box", padding: "20px 24px", borderRadius: 24, background: "rgba(5, 8, 14, .84)", border: "2px solid rgba(255,255,255,.88)", boxShadow: "0 8px 26px rgba(0,0,0,.38)", textAlign: "center", fontFamily: "Arial Black, Arial, sans-serif", fontSize: 48, fontWeight: 900, lineHeight: 1.18, textTransform: "uppercase", overflowWrap: "anywhere", wordBreak: "normal" }}>
        {line.tokens.map((token: any, i: number) => {
          const active = now >= (token.fromMs ?? 0) && now < (token.toMs ?? Infinity);
          return <span key={i} style={{ display: "inline", color: active ? "#FFE45E" : "#FFFFFF", WebkitTextStroke: "1px rgba(0,0,0,.65)", textShadow: active ? "0 0 12px rgba(255,228,94,.5)" : "0 2px 3px rgba(0,0,0,.6)", transition: "color 100ms linear" }}>{token.text}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};

const Klebee: React.FC<Props> = ({ videoPath, narrationPath, headline, middleHeadline, ctaHeadline, captionSegments }) => {
  const { durationInFrames } = useVideoConfig();
  const middleStart = Math.round(durationInFrames * 0.36);
  const ctaStart = Math.round(durationInFrames * 0.72);
  const ctaDuration = durationInFrames - ctaStart;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Video src={staticFile(videoPath)} style={{ width: "100%", height: "100%", objectFit: "cover" }} volume={0} />
      <Audio src={staticFile(narrationPath)} volume={1} />
      <Sequence from={0} durationInFrames={Math.min(Math.round(durationInFrames * 0.25), 105)}><Kicker text={headline} variant="hook" /></Sequence>
      <Sequence from={middleStart} durationInFrames={Math.max(1, Math.round(durationInFrames * 0.25))}><Kicker text={middleHeadline} variant="benefit" /></Sequence>
      <Sequence from={ctaStart} durationInFrames={ctaDuration}><Kicker text={ctaHeadline} variant="cta" /></Sequence>
      <Karaoke segments={captionSegments} />
    </AbsoluteFill>
  );
};

const Root: React.FC = () => <Composition
  id="KlebeeVideo"
  component={Klebee}
  durationInFrames={450}
  fps={30}
  width={1080}
  height={1920}
  defaultProps={{
    videoPath: "klebee-render-inputs/klebee-input.mp4",
    narrationPath: "klebee-render-inputs/klebee-voice.mp3",
    headline: "FRESCOR PORTÁTIL",
    middleHeadline: "PRATICIDADE ONDE VOCÊ ESTIVER",
    ctaHeadline: "VEJA NA SHOPEE",
    captionSegments: []
  }}
/>;
registerRoot(Root);
