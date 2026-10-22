# Avaliação técnica — OpenEdit no Super Robô Klebee

Data da avaliação: 2026-10-22

## Decisão

Usar OpenEdit como candidato para substituir o renderizador visual atual em um protótipo isolado, sem alterar `main` nem Railway. Não integrar diretamente ao serviço Railway neste momento: o renderizador OpenEdit exige sessão de desktop e roda localmente; um container web headless no Railway não atende esse requisito sem uma arquitetura adicional.

## O que pode agregar

- Transcrição com timestamps por palavra; rejeita legendas sem temporização adequada, evitando o SRT aproximado por quantidade de caracteres usado atualmente.
- Composição de legendas, títulos, motion graphics e enquadramento via HTML/CSS, com revisão visual orientada pelo agente.
- Composição de várias faixas de áudio, permitindo trilha, voz e efeitos no mesmo projeto.
- Uso de WhisperX local para transcrição sem custo de API (o primeiro download do modelo é grande e o processamento depende da máquina).
- Renderização local do MP4 e arquivos de execução em `runs/<id>/`, úteis para auditoria e repetição.

## Limitações e riscos confirmados

- OpenEdit está em beta; a própria documentação descreve motion graphics e styling como menos testados que legendas.
- O editor é gratuito/open source, mas o renderer distribuído usa licença separada PolyForm Shield 1.0.0; revisar o arquivo LICENSE/NOTICE da versão fixada antes de distribuir ou empacotar.
- A transcrição hospedada da VEED tem limites da conta. WhisperX local evita essa cobrança, mas exige instalação e recursos de máquina.
- Geração via VEED Fabric ou outros modelos não é automaticamente gratuita: pode consumir créditos ou chaves externas. Não habilitar geração paga sem aprovação explícita.
- OpenEdit não é, sozinho, um endpoint web pronto para produção. O fluxo é dirigido por um agente (Codex/Gemini/Claude) e o render acontece em máquina com sessão de desktop.
- A voz brasileira natural não está garantida apenas pela instalação do OpenEdit. O sistema precisa receber uma narração já gerada por TTS adequado ou conectar um provedor; a saída precisa ser testada quanto a pronúncia, prosódia e custo.
- Música pode ser composta/gerada por modelos acessíveis ao agente, mas isso não garante faixa gratuita, direitos de uso ou adequação automática. O fluxo Klebee deve ter biblioteca licenciada ou fornecedor configurado e mixagem validada.

## Diferenças para o endpoint atual

O endpoint `/gerar-video-real` usa gTTS, monta legendas SRT por fatias do texto, aplica uma faixa preta simples e não inclui trilha musical. Isso explica a temporização fraca e o resultado visual/sonoro básico. OpenEdit pode melhorar composição e alinhamento de legendas, mas não corrige automaticamente voz, trilha, seleção comercial de chamadas ou direitos de áudio sem integrações e critérios explícitos.

## Próximo teste técnico — sem produção

1. Fixar uma versão/commit do OpenEdit e inspecionar as licenças e os comandos disponíveis.
2. Executar em ambiente local com o vídeo real do ventilador, não com os fixtures sintéticos de CI.
3. Gerar transcrição com timestamps por palavra usando WhisperX local.
4. Criar composição vertical 9:16 com legendas dinâmicas legíveis, 2–3 chamadas comerciais e área segura para a interface da Shopee.
5. Usar narração pt-BR de fornecedor configurado e trilha de biblioteca com licença verificável; fazer ducking da música durante a fala.
6. Validar duração, sincronismo, legibilidade, clipping, loudness, voz e direitos dos ativos antes de aprovar o resultado.
7. Só depois de um MP4 real aprovado, decidir se vale criar um worker dedicado. Para Railway, considerar separar API/filas de um worker de render compatível com execução headless ou usar máquina local/serviço de render dedicado.

## Critérios de aceite

- MP4 real do produto, 9:16, sem barras indesejadas nem placeholders.
- Legendas alinhadas à fala palavra por palavra, sem fundo preto chapado por padrão, com estilo consistente.
- Narração pt-BR natural e inteligível.
- Música audível nos intervalos e abaixo da voz durante a fala, sem apitos ou áudio sintético de teste.
- Chamadas comerciais relevantes ao produto, sem cobrir o item nem a interface da plataforma.
- Render repetível, logs e fontes/ativos identificados.
- Nenhuma alteração em `main`/Railway sem aprovação explícita.
