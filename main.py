def enviar_para_drive(caminho_arquivo, nome_arquivo):
    creds = obter_credenciais()
    if not creds:
        return

    try:
        service = build('drive', 'v3', credentials=creds)
        
        # Garante que obtém a pasta autónoma criada pelo robô
        folder_id = obter_ou_criar_pasta_destino(service)
        if not folder_id:
            print("[Google Drive] Erro: Não foi possível obter a pasta de destino.")
            sys.stdout.flush()
            return

        caminho_absoluto = os.path.abspath(caminho_arquivo)

        # Associa o arquivo DIRETAMENTE dentro da pasta ID do robô
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(caminho_absoluto, mimetype='video/mp4', resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        print(f"[Google Drive] Vídeo enviado com sucesso para a pasta! ID: {file.get('id')}")
        sys.stdout.flush()
    except Exception as e:
        print(f"[Google Drive] Erro detalhado no upload: {e}")
        sys.stdout.flush()
