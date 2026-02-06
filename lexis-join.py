#!/usr/bin/env python3
import os
import re
import shutil
# Configurações de Limite (2MB é o ponto ideal para performance de texto puro)
MAX_FILE_SIZE_MB = 2 
MAX_CHARS = MAX_FILE_SIZE_MB * 1024 * 1024 

def process_content(content, filename):
    clean_text = ""
    summary_text = ""
    
    # Marcadores
    marker_transcription = "--- TRANSCRICAO COMPLETA ---"
    marker_summary = "--- RESUMO EXECUTIVO (VIA GEMINI) ---"
    
    # 1. Extração da Transcrição
    if marker_transcription in content:
        parts = content.split(marker_transcription)
        clean_text = parts[1].strip()
        
        # 2. Extração do Resumo (se houver metadados antes da transcrição)
        pre_transcription = parts[0]
        if marker_summary in pre_transcription:
            # Pega o que está entre o marcador de resumo e o final do bloco (que era onde começava a transcrição)
            summary_part = pre_transcription.split(marker_summary)[1].strip()
            summary_text = summary_part
    else:
        # Fallback para arquivos antigos ou sem formato definido
        clean_text = content.strip()
        # Remove timestamps de SRT se ainda existirem
        clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', clean_text)
        summary_text = "Resumo não encontrado no arquivo original."
    
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    full_text = ' '.join(lines)
    
    header = f"\n\n{'='*30}\nINÍCIO DO VÍDEO: {filename}\n{'='*30}\n"
    footer = f"\n{'='*30}\nFIM DO VÍDEO: {filename}\n{'='*30}\n"
    
    return header + full_text + footer, full_text, summary_text

def save_volume(channel, volume, content, compiled_summaries):
    output_name = f"CONSOLIDADO_{channel}_VOL_{volume:03d}.txt"
    with open(output_name, 'w', encoding='utf-8') as out:
        out.write(f"CANAL: {channel} | VOLUME: {volume}\n")
        out.write(f"--- COLETÂNEA DE RESUMOS DESTE VOLUME ---\n\n{compiled_summaries}\n\n")
        out.write(f"--- CONTEÚDO DOS VÍDEOS ---\n")
        out.write(content)
    print(f"✓ Arquivo gerado: {output_name}")

def process_channel(channel_path, channel_name):
    current_content = ""
    current_summaries_list = [] # Lista para acumular os resumos
    volume = 1
    
    files = [f for f in os.listdir(channel_path) 
             if f.endswith('.txt') and not f.startswith("CONSOLIDADO_")]
    if not files:
        return

    # Sort files to ensure deterministic order (optional but good practice)
    files.sort()
    
    print(f"--- Processando Canal: {channel_name} ---")

    # Garante que a pasta de archive existe
    archive_path = os.path.join(channel_path, ARCHIVE_DIR_NAME)
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    pending_archive = []

    for f in files:
        full_path = os.path.join(channel_path, f)
        with open(full_path, 'r', encoding='utf-8') as file:
            processed, _, summary_text = process_content(file.read(), f)
            
            # Formata o resumo para a lista
            formatted_summary = f"=== RESUMO: {f} ===\n{summary_text}"
            
            # 1. Adiciona o conteúdo ao volume atual
            current_content += processed
            current_summaries_list.append(formatted_summary)
            pending_archive.append(full_path)
            print(f"  > Adicionado (pendente archive): {f}")

            # 2. Verifica se estourou o limite APÓS adicionar
            # Se estourou, salva este volume e limpa para o próximo
            if len(current_content) > MAX_CHARS:
                print(f"  ! Volume {volume} atingiu o limite ({len(current_content)} chars). Salvando...")
                
                # Compila os resumos acumulados
                final_summary_block = "\n\n".join(current_summaries_list)
                save_volume(channel_name, volume, current_content, final_summary_block)
                
                # Move os arquivos que foram salvos neste volume para o archive
                for pending in pending_archive:
                    try:
                        shutil.move(pending, os.path.join(archive_path, os.path.basename(pending)))
                        print(f"  - Arquivado: {pending}")
                    except Exception as e:
                        print(f"  ! Erro ao arquivar {pending}: {e}")
                pending_archive = []
                
                volume += 1
                current_content = ""
                current_summaries_list = []
                # time.sleep(2) # Removido, sem API não precisa ser tão lento

    # Salva o último volume (ou o único)
    if current_content:
        final_summary_block = "\n\n".join(current_summaries_list)
        save_volume(channel_name, volume, current_content, final_summary_block)
        # Archive os arquivos restantes
        for pending in pending_archive:
            try:
                shutil.move(pending, os.path.join(archive_path, os.path.basename(pending)))
                print(f"  - Arquivado: {pending}")
            except Exception as e:
                print(f"  ! Erro ao arquivar {pending}: {e}")

def consolidate_by_channel(base_path):
    # 1. Process files in the current directory (base_path)
    base_files = [f for f in os.listdir(base_path) 
                  if f.endswith('.txt') and not f.startswith("CONSOLIDADO_")]
    if base_files:
        # Use directory name as channel name
        current_dir_name = os.path.basename(os.path.abspath(base_path))
        process_channel(base_path, current_dir_name)

    # 2. Process subdirectories
    dirs = [d for d in os.listdir(base_path) 
            if os.path.isdir(os.path.join(base_path, d)) and d != ARCHIVE_DIR_NAME]
    for d in dirs:
        process_channel(os.path.join(base_path, d), d)

if __name__ == "__main__":
    consolidate_by_channel('.')