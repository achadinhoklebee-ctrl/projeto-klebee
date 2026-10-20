def obter_ou_criar_pasta_destino(service):
    """Procura se a pasta já existe ou cria uma nova de forma autónoma"""
    try:
        # Tenta encontrar se o robô já criou esta pasta anteriormente
        query = "name = 'Fabrica_Videos_Shopee_Robot' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            # Se já existir, usa a pasta existente
            return files[0]['id']

        # Caso contrário, cria uma nova pasta
        file_metadata = {
            'name': 'Fabrica_Videos_Shopee_Robot',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        nova_pasta_id = folder.get('id')
        print(f"[Google Drive] Nova pasta criada pelo robô! ID: {nova_pasta_id}")
        
        # Partilha com a sua conta principal
        user_permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': EMAIL_PROPRIETARIO
        }
        service.permissions().create(
            fileId=nova_pasta_id,
            body=user_permission,
            fields='id'
        ).execute()
        
        return nova_pasta_id
    except Exception as e:
        print(f"[Google Drive] Erro ao gerir pasta autónoma: {e}")
        sys.stdout.flush()
        return None
