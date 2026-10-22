# Protótipo isolado Remotion — Klebee

Esta branch de teste adiciona um motor Remotion separado. Não altera `main` nem Railway.

## Requisitos para executar
- Node.js 18 ou superior
- Acesso ao registry npm para instalar dependências
- FFmpeg disponível no ambiente
- Vídeo MP4, narração MP3 e legendas alinhadas palavra por palavra

## Executar
```bash
npm install
npm run render:klebee -- ./video.mp4 ./narracao.mp3 ./captions.json ./resultado.mp4 "OLHA ESSE ACHADINHO!"
```

`captions.json` deve ser uma lista como:
```json
[
  { "text": "OLHA", "startMs": 0, "endMs": 260 },
  { "text": "ESSE", "startMs": 260, "endMs": 520 },
  { "text": "ACHADINHO", "startMs": 520, "endMs": 1050 }
]
```

Esses tempos são apenas um exemplo de formato, não uma transcrição real. Para o vídeo final, os tempos precisam ser obtidos por alinhamento/transcrição do áudio.

## Estado honesto
O protótipo contém headline laranja animada caractere por caractere, destaque karaoke da palavra ativa, formato vertical 1080x1920 e áudio original reduzido para 16% sob a narração. Ainda não foi possível executar `npm install` nem renderizar um MP4 neste ambiente porque a conexão de rede para o registry/GitHub falha na resolução DNS. Portanto, o código está na branch isolada, mas o resultado visual ainda precisa ser renderizado e validado antes de qualquer uso em produção.


## Regra de validação do produto (atualização)

O workflow de CI usa vídeo, narração e legendas sintéticos apenas para verificar que o motor consegue renderizar. Esse arquivo de smoke test **não é uma entrega de produto** e não deve ser enviado ao usuário para avaliação criativa. O workflow não publica mais esse MP4 sintético como artefato.

Uma validação real deve usar o vídeo original do produto, narração falada em português brasileiro, legendas revisadas e sincronizadas com a fala e trilha musical adequada. A aprovação do CI comprova apenas compatibilidade técnica, não qualidade audiovisual nem conclusão da automação ponta a ponta.
