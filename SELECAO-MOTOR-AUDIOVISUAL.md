# Seleção de motor audiovisual — Super Robô Klebee

Data: 2026-10-22
Escopo: pesquisa de código e documentação pública; nenhuma instalação, cobrança, alteração em `main` ou deploy foi executado.

## Decisão provisória baseada no requisito de baixo custo

**Candidato A para o próximo teste: OpenEdit. Candidato B: OpenFilm. Não integrar Framedeck ainda.**

### Por que OpenEdit fica primeiro

- Resolve um problema que hoje está comprovadamente quebrado no endpoint Klebee: as legendas atuais são divididas por quantidade de caracteres e por tempos fixos, não alinhadas à fala.
- Exige temporização palavra por palavra e oferece WhisperX local, sem custo de API de transcrição.
- Renderiza no computador local, com composição por HTML/CSS, títulos animados e múltiplas faixas de áudio.
- Código do editor sob Apache-2.0; o binário do renderer tem licença separada PolyForm Shield 1.0.0. Revisar a licença antes de empacotar/distribuir, embora a documentação permita uso comercial dos vídeos produzidos.
- O projeto é orientado por agente (Gemini CLI, Codex ou Claude Code), não é um backend web plug-and-play.

Fontes: https://github.com/veedstudio/open-edit ; https://github.com/veedstudio/open-edit/blob/main/AGENTS.md

### Por que manter OpenFilm como alternativa real

- MIT e local, sem conta obrigatória para editar/renderizar; permite timeline de vídeo, títulos, animação e faixas de áudio.
- A voz, música e geração de mídia dependem de provedores escolhidos; conectar serviços externos pode gerar custos. Portanto, “OpenFilm grátis” não significa “toda IA grátis”.
- Não foi confirmado que ofereça por si só transcrição pt-BR com alinhamento palavra por palavra equivalente ao OpenEdit. Precisaria ligar uma ferramenta local de transcrição e validar.

Fontes: https://github.com/openfilm/openfilm ; https://openfilm.dev/

### Por que não selecionar Framedeck agora

- O site anuncia edição por linguagem natural, legendas palavra por palavra, overlays e renderização cloud via Remotion.
- O repositório é público, mas os metadados consultados não identificaram licença no GitHub API, apesar de o site anunciar MIT. Não adotar nem incorporar código até confirmar o arquivo LICENSE e a arquitetura de custos.
- Análise de vídeo via TwelveLabs e uploads/renderização em nuvem podem exigir credenciais/serviços; isso não satisfaz automaticamente o objetivo de custo zero.

Fontes: https://github.com/kevinrss01/framedeck ; https://framedeck.ai/

## Compatibilidade com a infraestrutura Klebee

A arquitetura atual mistura a API Flask e um renderizador simples. O endpoint `/gerar-video-real`:
1. gera narração por gTTS;
2. divide texto em blocos SRT com durações fixas, sem alinhamento de fala;
3. desenha headline e legenda básica no FFmpeg;
4. não seleciona nem adiciona trilha musical;
5. usa caminhos temporários fixos, arriscando colisões em tarefas concorrentes.

Por isso, trocar apenas a camada visual não conclui a automação. A futura arquitetura deve separar:
- API de upload/solicitação;
- worker de processamento isolado por job;
- narração TTS pt-BR configurável;
- transcrição/alinhamento palavra por palavra;
- renderizador de composição;
- biblioteca de trilhas com direitos de uso registrados;
- mixagem/ducking e validação;
- armazenamento e link de download persistente.

## Próximo teste, sem custo de API e sem produção

1. Rodar OpenEdit numa cópia isolada, com WhisperX local e o vídeo real `TESTE-CHATGPT.mp4`.
2. Para voz, verificar primeiro TTS local com voz pt-BR disponível e qualidade aceitável; não assumir que gTTS soa natural. Se a voz gratuita local falhar, comparar opções e custos antes de escolher.
3. Usar música de uma biblioteca licenciada local, não um gerador pago por padrão.
4. Renderizar um MP4 real de 15 segundos e avaliar: voz, pronúncia, legendas sincronizadas, chamadas, música/ducking, formato 9:16 e legibilidade.
5. Registrar requisitos de instalação e execução. Se OpenEdit exigir sessão desktop incompatível com worker, testar OpenFilm para a composição e manter WhisperX/alinhamento local como serviço separado.
6. Somente após o MP4 real aprovado, decidir se cria um worker independente. Não enviar esse renderizador desktop diretamente ao Railway sem desenho de execução headless e fila.

## Bloqueio operacional encontrado neste ambiente

O vídeo real existe em `/mnt/data/files/TESTE-CHATGPT.mp4`; FFmpeg está disponível. O Node disponível é 22.16.0, abaixo do requisito publicado pelo OpenFilm (22.18+), e este ambiente não tem acesso de rede funcional para instalar pacotes npm/baixar modelos. Assim, não é possível afirmar que a execução local foi concluída aqui. Isso não impede preparar a integração, mas impede honestamente validar o MP4 gerado neste ambiente.

## Regra de aceite

Não declarar sucesso com base em CI sintético, logs de compilação ou existência de arquivo. Só considerar aprovado depois de abrir/escutar um MP4 feito com o vídeo real e conferir os critérios audiovisuais acima.
