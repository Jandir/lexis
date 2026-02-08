"""
SCRIPT: lexis.py
DESCRIÇÃO:
    Este script processa arquivos de legenda (.srt) no diretório atual.
    Ele realiza as seguintes etapas para cada arquivo:
    1. Limpa o texto, removendo timestamps e formatações.
    2. Extrai metadados do arquivo .info.json correspondente (se existir).
    3. Utiliza a API do Google Gemini para gerar um resumo executivo do conteúdo.
    4. Salva o resultado (Metadados + Resumo + Transcrição Limpa) em um arquivo .txt.
    5. Arquiva o arquivo .srt original na pasta 'arquive' para evitar reprocessamento.

USO:
    Execute o script na pasta contendo os arquivos .srt.
    Certifique-se de ter o arquivo .env configurado com a GEMINI_API_KEY.
"""
import os
import re
import time
import json
import glob
import shutil
import concurrent.futures
# Removed deprecated import
from google import genai
from google.genai import types

# --- CONFIGURAÇÃO DA IA (ATUALIZADA) ---
from dotenv import dotenv_values

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
env_vars = dotenv_values(env_path)
api_key = env_vars.get("GEMINI_API_KEY")

if not api_key:
    print(f"ERRO: A variável GEMINI_API_KEY não foi encontrada no arquivo .env em: {env_path}")
    print("Por favor, crie um arquivo .env com: GEMINI_API_KEY=sua_chave_aqui")
    exit(1)

client = genai.Client(api_key=api_key)
MODEL_ID = 'gemini-flash-latest'

# Cores para o terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Pré-compilação de Regex para performance
REGEX_TIMESTAMPS = re.compile(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')
REGEX_HTML = re.compile(r'<[^>]+>')
REGEX_SENTENCE_SPLIT = re.compile(r'(?<=[.!?]) +')


def get_ai_summary(text):
    """Gera um resumo executivo para servir de mapa ao NotebookLM"""
    # Se o texto for muito curto, não gasta API
    if len(text) < 50:
        return "Texto muito curto para gerar resumo."

    prompt = f"""
    Atue como um analista de conteúdo sênior. Abaixo está a transcrição de um vídeo.
    Gere um resumo executivo de 3 parágrafos focando nos conceitos-chave, 
    teologias mencionadas ou insights técnicos.
    Este resumo será usado como metadado para um sistema de RAG (NotebookLM).
    
    Texto: {text[:10000]} # Limitando para não estourar o prompt inicial
    """
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"{Colors.FAIL}Erro ao gerar resumo (API): {e}{Colors.ENDC}")
        return ""


def process_srt_content(content, overlap_sentences=2):
    """
    Limpa o conteúdo do SRT, removendo timestamps e formatando.
    Retorna (texto_formatado_rag, texto_completo_limpo)
    """
    # 1. Limpeza de metadados do SRT (timestamps, números)
    # Remove: 123 \n 00:00:00,000 --> 00:00:00,000
    clean_text = REGEX_TIMESTAMPS.sub('', content)
    
    # Remove tags HTML se houver
    clean_text = REGEX_HTML.sub('', clean_text)
    
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    full_text = ' '.join(lines)
    
    # 2. Divisão em sentenças e agrupamento com Overlap (para RAG, opcional aqui mas mantido)
    sentences = REGEX_SENTENCE_SPLIT.split(full_text)
    paragraphs = []
    chunk_size = 12 
    
    for i in range(0, len(sentences), chunk_size - overlap_sentences):
        chunk = sentences[i : i + chunk_size]
        paragraphs.append(" ".join(chunk))
        if i + chunk_size >= len(sentences): break
            
    # Retorna o texto formatado em parágrafos e o texto corrido limpo
    return "\n\n".join(paragraphs), full_text

def get_metadata(srt_filename):
    """
    Busca metadados no arquivo .info.json correspondente, se existir.
    """
    base_name = os.path.splitext(srt_filename)[0]
    
    # Tenta encontrar o .info.json (às vezes tem sufixos de língua como .en.srt -> .en.info.json ou apenas .info.json)
    # Assumindo que o json tem o mesmo prefixo base
    # Ex: video.srt -> video.info.json
    # Ex: video.en.srt -> video.info.json (mais complexo, vamos tentar o exato primeiro)
    
    candidates = [
        base_name + ".info.json",
        base_name.rsplit('.', 1)[0] + ".info.json" if '.' in base_name else None
    ]
    
    for json_path in candidates:
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        "date": data.get('upload_date', 'Desconhecida'),
                        "title": data.get('title', 'Sem Título'),
                        "id": data.get('id', 'Sem ID')
                    }
            except Exception as e:
                print(f"Erro ao ler JSON {json_path}: {e}")
    
    return {"date": "Desconhecida", "title": base_name, "id": "N/A"}

def main():
    # Define o diretório de trabalho como o diretório atual
    current_dir = os.getcwd()
    print(f"Iniciando processamento em: {current_dir}")
    
    # Busca todos os arquivos .srt
    srt_files = glob.glob("*.srt")
    
    if not srt_files:
        print("Nenhum arquivo .srt encontrado na pasta atual.")
        return

    print(f"Encontrados {len(srt_files)} arquivos .srt.")

def process_file(filename, current_dir):
    """Processa um único arquivo SRT. Função isolada para rodar em thread."""
    # Define nome de saída antecipadamente para verificar existência
    output_filename = os.path.splitext(filename)[0] + ".txt"
    
    if os.path.exists(output_filename):
        print(f"{Colors.WARNING}⚠ [SKIP] {filename} -> {output_filename} já existe.{Colors.ENDC}")
        return filename, False

    try:
        success = False # Flag de controle
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()
        
        # Limpa o texto
        _, clean_full_text = process_srt_content(raw_content)
        
        if not clean_full_text.strip():
            print(f"{Colors.WARNING}⚠ [VAZIO] {filename} resultou em texto vazio.{Colors.ENDC}")
            return filename, False

        # Obtém metadados
        meta = get_metadata(filename)
        
        # Gera resumo (Gemini)
        # print(f"Gerando resumo para: {filename}...") 
        summary = get_ai_summary(clean_full_text)
        
        # Se o resumo veio vazio, significa erro na API. 
        # Decisão: Ainda salvamos o arquivo TXT (pois tem a transcrição), 
        # mas NÃO marcaremos success=True para não arquivar o original e permitir retry do resumo depois?
        # OU salvamos sem resumo e consideramos sucesso parcial?
        # O usuário pediu: "Se houver erro qualquer, não mova o arquivo"
        # Se a API falhar, o summary é "". Isso pode ser considerado um "erro parcial".
        # Para garantir que ele possa tentar de novo o resumo, NÃO vamos arquivar.
        
        if not summary:
             print(f"{Colors.WARNING}⚠ [SEM RESUMO] {filename} -> Salvo (SRT mantido).{Colors.ENDC}")
             # success continua False
        else:
             success = True
        
        # Formata a data se for YYYYMMDD
        date_str = meta['date']
        if len(date_str) == 8 and date_str.isdigit():
            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

        # Prepara o conteúdo final
        final_content = (
            f"--- METADADOS DO DOCUMENTO ---\n"
            f"DATA: {date_str}\n"
            f"TÍTULO: {meta['title']}\n"
            f"ID: {meta['id']}\n\n"
            f"--- RESUMO EXECUTIVO (VIA GEMINI) ---\n"
            f"{summary}\n\n"
            f"--- TRANSCRICAO COMPLETA ---\n"
            f"{clean_full_text}\n"
        )
        
        with open(output_filename, 'w', encoding='utf-8') as f_out:
            f_out.write(final_content)
            
        print(f"{Colors.GREEN}✓ [OK] {filename} -> {output_filename}{Colors.ENDC}")

        return filename, success
            
    except Exception as e:
        print(f"{Colors.FAIL}✖ [ERRO] {filename}: {e}{Colors.ENDC}")
        return filename, False

def main():
    # Define o diretório de trabalho como o diretório atual
    current_dir = os.getcwd()
    print(f"Iniciando processamento em: {current_dir}")
    
    # Busca todos os arquivos .srt
    srt_files = glob.glob("*.srt")
    
    if not srt_files:
        print(f"{Colors.WARNING}Nenhum arquivo .srt encontrado na pasta atual.{Colors.ENDC}")
        return

    print(f"{Colors.BLUE}Encontrados {len(srt_files)} arquivos .srt. Iniciando processamento paralelo (max 5 threads)...{Colors.ENDC}")

    success_files = []
    
    # Utiliza ThreadPoolExecutor para processar arquivos em paralelo
    # Isso acelera drasticamente pois as chamadas de API são I/O bound
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Mapeia a função process_file para cada arquivo na lista
        futures = [executor.submit(process_file, filename, current_dir) for filename in srt_files]
        
        # Aguarda conclusão e coleta resultados
        for future in concurrent.futures.as_completed(futures):
            try:
                fname, success = future.result()
                if success:
                    success_files.append(fname)
            except Exception as e:
                print(f"{Colors.FAIL}Erro na thread: {e}{Colors.ENDC}")

    print(f"{Colors.GREEN}\n--- Processamento concluído. Iniciando Arquivamento ---{Colors.ENDC}")
    
    # Arquivamento em lote
    if success_files:
        archive_dir = os.path.join(current_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        print(f"{Colors.BLUE}Arquivando {len(success_files)} arquivos com sucesso...{Colors.ENDC}")
        
        for filename in success_files:
             # Safety check: ensure .txt exists before archiving .srt
             txt_filename = os.path.splitext(filename)[0] + ".txt"
             if not os.path.exists(txt_filename):
                 print(f"{Colors.FAIL}CRÍTICO: .txt não encontrado para {filename}. Não arquivando.{Colors.ENDC}")
                 continue

             try:
                shutil.move(filename, os.path.join(archive_dir, filename))
                print(f"{Colors.GREEN}Arquivado: {filename}{Colors.ENDC}")
             except Exception as e:
                print(f"{Colors.FAIL}Erro ao arquivar {filename}: {e}{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Nenhum arquivo elegível para arquivamento.{Colors.ENDC}")

    print(f"{Colors.GREEN}\n--- Processamento concluído ---{Colors.ENDC}")
    print(f"{Colors.BLUE}Modelo utilizado: {Colors.BOLD}{MODEL_ID}{Colors.ENDC}")

if __name__ == "__main__":
    main()