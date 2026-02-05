import os
import re
import time
import json
import glob
import shutil
# Removed deprecated import
from google import genai
from google.genai import types

# --- CONFIGURAÇÃO DA IA (ATUALIZADA) ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERRO: A variável de ambiente GEMINI_API_KEY não está definida.")
    print("Por favor, defina-a com: export GEMINI_API_KEY='sua_chave_aqui'")
    exit(1)

client = genai.Client(api_key=api_key)
MODEL_ID = 'gemini-2.5-flash'

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
        return f"Erro ao gerar resumo: {e}"

def process_srt_content(content, overlap_sentences=2):
    """
    Limpa o conteúdo do SRT, removendo timestamps e formatando.
    Retorna (texto_formatado_rag, texto_completo_limpo)
    """
    # 1. Limpeza de metadados do SRT (timestamps, números)
    # Remove: 123 \n 00:00:00,000 --> 00:00:00,000
    clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
    
    # Remove tags HTML se houver
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    full_text = ' '.join(lines)
    
    # 2. Divisão em sentenças e agrupamento com Overlap (para RAG, opcional aqui mas mantido)
    sentences = re.split(r'(?<=[.!?]) +', full_text)
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

    for filename in srt_files:
        print(f"\n--- Processando: {filename} ---")
        
        # Define nome de saída antecipadamente para verificar existência
        output_filename = os.path.splitext(filename)[0] + ".txt"
        
        if os.path.exists(output_filename):
            print(f"Skipping: {filename} -> {output_filename} já existe.")
            continue

        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                raw_content = f.read()
            
            # Limpa o texto
            # url_rag_formatted, full_clean_text = process_srt_content(raw_content)
            # Vamos usar o full_clean_text para o resumo e para o corpo principal
            _, clean_full_text = process_srt_content(raw_content)
            
            if not clean_full_text.strip():
                print(f"Aviso: Arquivo {filename} resultou em texto vazio. Pulando.")
                continue

            # Obtém metadados
            meta = get_metadata(filename)
            
            # Gera resumo (Gemini)
            print("Gerando resumo com IA...")
            summary = get_ai_summary(clean_full_text)
            
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
            
            # Define nome de saída (já definido acima, mas mantendo a lógica de uso)
            
            with open(output_filename, 'w', encoding='utf-8') as f_out:
                f_out.write(final_content)
                
            print(f"Salvo: {output_filename}")

            # Arquivar o arquivo original
            archive_dir = os.path.join(current_dir, "arquive")
            os.makedirs(archive_dir, exist_ok=True)
            try:
                shutil.move(filename, os.path.join(archive_dir, filename))
                print(f"Arquivado: {filename} -> {archive_dir}")
            except Exception as e:
                print(f"Erro ao arquivar {filename}: {e}")
            
            # Delay
            time.sleep(2)
            
        except Exception as e:
            print(f"ERRO FATAL ao processar {filename}: {e}")

if __name__ == "__main__":
    main()