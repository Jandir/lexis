#!/usr/bin/env python3
import os
import re
from google import genai
import time

# Configuração da API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERRO: A variável de ambiente GEMINI_API_KEY não está definida.")
    exit(1)

client = genai.Client(api_key=api_key)
MODEL_ID = 'gemini-2.5-flash'

# Configurações de Limite (2MB é o ponto ideal para performance de texto puro)
MAX_FILE_SIZE_MB = 2 
MAX_CHARS = MAX_FILE_SIZE_MB * 1024 * 1024 

def process_srt(content, filename):
    clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    full_text = ' '.join(lines)
    
    header = f"\n\n{'='*30}\nINÍCIO DO VÍDEO: {filename}\n{'='*30}\n"
    footer = f"\n{'='*30}\nFIM DO VÍDEO: {filename}\n{'='*30}\n"
    
    return header + full_text + footer, full_text

def get_summary(text):
    prompt = f"Gere um resumo técnico/teológico de 5 pontos principais para indexação RAG: {text[:8000]}"
    try:
        return client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        ).text
    except:
        return "Resumo indisponível."

def save_volume(channel, volume, content, raw_text):
    summary = get_summary(raw_text)
    output_name = f"CONSOLIDADO_{channel}_VOL_{volume}.txt"
    with open(output_name, 'w', encoding='utf-8') as out:
        out.write(f"CANAL: {channel} | VOLUME: {volume}\n")
        out.write(f"RESUMO DO VOLUME:\n{summary}\n\n")
        out.write(content)
    print(f"✓ Arquivo gerado: {output_name}")

def process_channel(channel_path, channel_name):
    current_content = ""
    current_raw = ""
    volume = 1
    
    files = [f for f in os.listdir(channel_path) if f.endswith('.srt')]
    if not files:
        return

    # Sort files to ensure deterministic order (optional but good practice)
    files.sort()
    
    print(f"--- Processando Canal: {channel_name} ---")

    for f in files:
        with open(os.path.join(channel_path, f), 'r', encoding='utf-8') as file:
            processed, raw = process_srt(file.read(), f)
            
            # Verifica se a adição deste vídeo estoura o limite do volume
            # O check 'if current_content' garante que não salvamos um volume vazio se o primeiro vídeo já for maior que o limite
            # Isso assegura que um vídeo nunca será "quebrado" ao meio; ele vai inteiro para o próximo volume se não couber no atual
            if current_content and (len(current_content) + len(processed) > MAX_CHARS):
                save_volume(channel_name, volume, current_content, current_raw)
                volume += 1
                current_content = ""
                current_raw = ""
                time.sleep(2) # Respiro para a API
            
            current_content += processed
            current_raw += raw + " "
            print(f"  > Adicionado: {f}")

    # Salva o último volume (ou o único)
    if current_content:
        save_volume(channel_name, volume, current_content, current_raw)

def consolidate_by_channel(base_path):
    # 1. Process files in the current directory (base_path)
    base_files = [f for f in os.listdir(base_path) if f.endswith('.srt')]
    if base_files:
        # Use directory name as channel name
        current_dir_name = os.path.basename(os.path.abspath(base_path))
        process_channel(base_path, current_dir_name)

    # 2. Process subdirectories
    dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    for d in dirs:
        process_channel(os.path.join(base_path, d), d)

if __name__ == "__main__":
    consolidate_by_channel('.')