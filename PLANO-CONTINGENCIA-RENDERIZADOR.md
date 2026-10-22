# Plano de contingência — abandonar dependência do OpenEdit

Data: 2026-10-22

## Decisão

Não bloquear o Super Robô Klebee no OpenEdit. O candidato alternativo prioritário para a próxima prova técnica é **Reframe** (https://github.com/Prekzursil/Reframe), por ser local-first e reunir legenda karaoke palavra por palavra, presets de legendas, mixagem/ducking, TTS por múltiplos motores, normalização de áudio e pipelines. O repositório declara execução offline com modelos locais e FFmpeg. Isso corresponde melhor aos requisitos do vídeo Shopee e reduz dependência de API paga.

**Plano B:** OpenChatCut (https://github.com/jeffreycayao/openchatcut), por ter timeline multifaixa, legendas automáticas, templates de motion graphics, narração, música e auto-ducking, com integração MCP/agent. Atenção: verificar licença AGPL-3.0 e possíveis implicações antes de incorporar código ao produto.

**Plano C:** dawn-cut (https://github.com/kwakseongjae/dawn-cut), para reutilizar o núcleo de timeline, legendas, overlays, TTS local e render FFmpeg. É v0.1 e os recursos de edição em linguagem natural ainda são experimentais; o auto-subtitle publicado é focado em coreano, então não deve ser escolhido como motor principal para pt-BR sem testar a transcrição.

## Fontes e recursos publicados

- Reframe: https://github.com/Prekzursil/Reframe
  - Whisper local / faster-whisper, legendas com destaque palavra por palavra, estilos karaoke, TTS multi-engine (Kokoro, Chatterbox, edge-tts), dub, mixagem A/V, sidechain ducking e loudness EBU R128; receitas de pipeline; opção offline.
  - Tem uma rota de distribuição local; avaliar se o motor pode ser isolado como worker sem trazer toda a interface para Railway.
- OpenChatCut: https://github.com/jeffreycayao/openchatcut
  - Timeline profissional multifaixa, geração de legendas, títulos/templates, música, narração, auto-ducking, rendering Remotion, integração MCP/agent.
  - Projeto fork e licença AGPL-3.0 indicada na página pública; revisar implicações antes de uso comercial/distribuição.
- dawn-cut: https://github.com/kwakseongjae/dawn-cut
  - Núcleo TypeScript determinístico, Whisper.cpp word timestamps, FFmpeg, overlays animados, TTS macOS local/Piper opcional, estilos pré-definidos.
  - v0.1; natural-language editing/agent é experimental e legendas automáticas publicadas são em coreano.

## Ação imediata proposta

1. Usar Reframe como referência/engine candidato, sem tocar em main/Railway.
2. Verificar licença, requirements e o caminho mais curto para rodar localmente no Windows com o vídeo real do ventilador.
3. Confirmar voz pt-BR gratuita que rode localmente e seja inteligível. Se Kokoro/Chatterbox/edge-tts não entregarem qualidade ou disponibilidade de voz aceitável em português, testar alternativa local antes de qualquer serviço pago.
4. Gerar legenda word-level usando transcrição/alinhamento real, não segmentação por caracteres.
5. Usar uma faixa musical local com licença documentada e ducking durante fala.
6. Renderizar e inspecionar o MP4 real; não aceitar apenas teste sintético/CI.
7. Se o editor inteiro não puder ser integrado ao Railway, extrair/encapsular somente as funções de transcrição, TTS, composição e render em worker isolado. A API e a fila ficam separadas do processo de render.
8. Caso Reframe não rode ou seja incompatível, passar diretamente ao OpenChatCut; não gastar tempo tentando destravar OpenEdit.

## Estado

Este é um plano de contingência baseado em inspeção de documentação/repositórios públicos. Ainda não foi executada a aplicação Reframe nem gerado um MP4 usando-a. O ambiente de execução atual não tem acesso funcional ao registry/model downloads; não afirmar que o teste passou até que haja um render real verificável.
