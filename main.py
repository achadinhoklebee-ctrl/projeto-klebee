import os
import sys
import time
import json
import subprocess
import traceback

print("=== [1/6] INICIANDO SCRIPT PRINCIPAL ===", flush=True)

try:
    print("=== [2/6] CARREGANDO DEPENDÊNCIAS DO GOOGLE E FFMPEG ===", flush=True)
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    print("-> Bibliotecas importadas com sucesso!", flush=True)
except Exception as e:
    print(f"CRÍTICO: Erro ao importar bibliotecas: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

def autenticar_drive():
    print("=== [3/6] AUTENTICANDO COM O GOOGLE DRIVE ===", flush=True)
    try:
        service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_info:
            raise ValueError("A variável de ambiente GOOGLE_SERVICE_ACCOUNT_JSON não foi encontrada.")
        
        creds_dict = json.loads(service_account_info)
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        
        print("-> Autenticação no Google Drive concluída com sucesso!", flush=True)
        return service
    except Exception as e:
        print(f"CRÍTICO: Erro na autenticação do Google Drive: {e}", flush=True)
        traceback.print_exc()
        return None

def enviar_para_drive(service, caminho_arquivo, folder_id):
    """Função para enviar vídeo para a pasta designada sem disparar notificações por e-mail."""
    try:
        nome_arquivo = os.path.basename(caminho_arquivo)
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_arquivo, resumable=True)
        
        print(f"A enviar '{nome_arquivo}' para o Google Drive...", flush=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            sendNotificationEmail=False
        ).execute()
        
        print(f"-> Upload concluído com sucesso! ID no Drive: {file.get('id')}", flush=True)
    except Exception as e:
        print(f"Erro ao enviar arquivo para o Drive: {e}", flush=True)

def gerar_video_ffmpeg(nome_saida="video_shopee.mp4"):
    """Gera um vídeo utilizando o FFmpeg diretamente no ambiente do Railway."""
    print(f"Iniciando renderização do vídeo com FFmpeg: {nome_saida}", flush=True)
    
    comando = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:d=5",
        "-vf", "drawtext=text='ACHADINHOS SHOPEE':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        nome_saida
    ]
    
    try:
        resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if resultado.returncode == 0:
            print("-> Vídeo gerado com sucesso via FFmpeg!", flush=True)
            return True
        else:
            print(f"Erro no FFmpeg: {resultado.stderr}", flush=True)
            return False
    except Exception as e:
        print(f"Exceção ao executar FFmpeg: {e}", flush=True)
        return False

def loop_principal():
    print("=== [4/6] INICIALIZANDO O SERVIÇO DO DRIVE ===", flush=True)
    drive_service = autenticar_drive()
    
    if not drive_service:
        print("CRÍTICO: Não foi possível conectar ao Drive. Encerrando execução.", flush=True)
        sys.exit(1)
        
    # Cole o ID da sua pasta do Google Drive entre as aspas abaixo:
    FOLDER_ID = "COLE_O_ID_DA_SUA_PASTA_AQUI" 
        
    print("=== [5/6] ENTRANDO NO LOOP CONTINUO DO ROBÔ ===", flush=True)
    
    ciclo = 1
    while True:
        print(f"--- [CICLO {ciclo}] Iniciando produção do lote de vídeos ---", flush=True)
        
        arquivo_video = f"shopee_video_{ciclo}.mp4"
        
        # 1. Gera o vídeo
        sucesso_geracao = gerar_video_ffmpeg(arquivo_video)
        
        # 2. Envia para a pasta informada e remove o arquivo local
        if sucesso_geracao and os.path.exists(arquivo_video):
            enviar_para_drive(drive_service, arquivo_video, FOLDER_ID)
            try:
                os.remove(arquivo_video)
                print(f"-> Arquivo temporário {arquivo_video} removido do disco.", flush=True)
            except Exception as ex:
                print(f"Aviso ao remover arquivo local: {ex}", flush=True)
                
        print(f"--- [CICLO {ciclo}] Concluído. Aguardando próximo intervalo... ---", flush=True)
        ciclo += 1
        time.sleep(60)

if __name__ == "__main__":
    print("=== [6/6] EXECUÇÃO DO BLOCO MAIN ===", flush=True)
    loop_principal()
