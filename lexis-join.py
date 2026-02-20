#!/usr/bin/env python3
import os
import re
import shutil

# Pasta de Arquivo morto das .srt originais baixadas do Youtube
# O usuário fica responsável por apagar essa pasta quando quiser.
ARCHIVE_DIR_NAME = "archive" 

# Configurações de Limite
# 1.8MB (aprox. 1.8 * 1024 * 1024 caracteres) é considerado o ponto ideal de performance
# e janela de contexto estendida ao integrar esses volumes de texto puro no NotebookLM.
MAX_FILE_SIZE_MB = 1.8
MAX_CHARS = MAX_FILE_SIZE_MB * 1024 * 1024 

def clean_srt_content(content):
    """
    Função principal: 
    Remove formatações HTML, limpa timestamps e desduplica linhas repetitivas 
    decrustadas pelo efeito de "roll-up" automático de legendas do YouTube.
    Isso otimiza e encurta vastamente o tamanho do arquivo destino para a IA processar.
    
    Processo de desduplicação:
    - O Youtube envia blocos encadeados tipo:
      Bloco N: "Palavra 1"
      Bloco N+1: "Palavra 1 \n Palavra 2", etc.
    - Essa técnica varre os arrays sobrepostos para capturar puramente strings inéditas de cada linha de tempo.
    """
    # Normaliza quebras de linha
    content = content.replace('\r\n', '\n')
    
    # Regex para identificar blocos de legenda:
    # Número
    # Timestamp --> Timestamp
    # Texto... (pode ter várias linhas)
    # \n (linha em branco separadora)
    
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*?)(?=\n\n|$)', re.DOTALL)
    
    blocks = []
    for match in pattern.finditer(content):
        text_block = match.group(4).strip()
        
        # Limpa tags HTML
        text_block = re.sub(r'<[^>]*>', '', text_block)
        
        if text_block:
            blocks.append(text_block)

    # Deduplicação lógica
    cleaned_lines = []
    if blocks:
        # Adiciona o primeiro bloco inteiro
        current_text = blocks[0]
        cleaned_lines.append(current_text)
        
        for i in range(1, len(blocks)):
            prev_text = blocks[i-1]
            curr_text = blocks[i]
            
            # Caso 1: Bloco atual começa com o bloco anterior
            if curr_text.startswith(prev_text):
                # Pega apenas o que vem depois
                new_part = curr_text[len(prev_text):].strip()
                if new_part:
                    cleaned_lines.append(new_part)
                continue
                
            prev_lines = [l.strip() for l in prev_text.split('\n') if l.strip()]
            curr_lines = [l.strip() for l in curr_text.split('\n') if l.strip()]
            
            start_idx = 0
            if prev_lines and curr_lines:
                if curr_lines[0] == prev_lines[-1]:
                    start_idx = 1
                elif len(prev_lines) < len(curr_lines) and curr_lines[:len(prev_lines)] == prev_lines:
                    start_idx = len(prev_lines)

            for j in range(start_idx, len(curr_lines)):
                cleaned_lines.append(curr_lines[j])

    return ' '.join(cleaned_lines)

import json

def get_metadata(srt_filename):
    """
    Função principal:
    Lê atributos do arquivo `.info.json` para preencher os Metadados do RAG (Data, Título e ID).
    
    Lógica:
    Como os downloads podem gerar artefatos terminados com sufixos diferentes ex: 'nomedovideo.pt.srt',
    o script itera descobrindo qual foi o prefixo literal original extraindo hífenes e pontos 
    até casar com a formatação exata do arquivo `.info.json`.
    """
    base_name = os.path.splitext(srt_filename)[0]
    
    candidates = [base_name + ".info.json"]
    
    temp_name = base_name
    while '.' in temp_name:
        temp_name = temp_name.rsplit('.', 1)[0]
        if temp_name:
            candidates.append(temp_name + ".info.json")

    temp_name = base_name
    while '-' in temp_name:
        temp_name = temp_name.rsplit('-', 1)[0]
        if temp_name:
             candidates.append(temp_name + ".info.json")
    
    candidates = list(dict.fromkeys(candidates))

    for json_path in candidates:
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        "date": data.get('upload_date', 'Desconhecida'),
                        "title": data.get('title', 'Sem Título'),
                        "id": data.get('id', 'Sem ID')
                    }
            except Exception:
                pass
    
    return {
        "date": "Desconhecida",
        "title": "Sem Título",
        "id": "Sem ID"
    }

def process_content(content, filename, full_path):
    """
    Função principal:
    Ingere a string bruta de um vídeo (seja .srt de download ou um .txt gerado previamente),
    parseia o bloco original e reestrutura esse payload acoplando os metadados mais legíveis 
    para alimentar como Volume consolidado no NotebookLM.
    
    Retorno:
    Tupla de 3 itens sendo o 1º a "Formatação Consolidada" e o 2º item o "Texto Crú" contíguo da transcrição.
    A extração do Resumo (3º item) foi desativada desta listagem mas mantido o parse reverso 
    para segurança de compatibilidade com modelos antigos de .txt.
    """
    clean_text = ""
    summary_text = ""
    metadata = {}
    full_metadata_str = ""
    
    # Marcadores
    marker_metadata = "--- METADADOS DO DOCUMENTO ---"
    marker_transcription = "--- TRANSCRICAO COMPLETA ---"
    marker_summary = "--- RESUMO EXECUTIVO (VIA GEMINI) ---"
    
    # 0. Extração de Metadados
    if marker_metadata in content:
        try:
            # Pega o bloco entre METADADOS e o próximo marcador (usualmente RESUMO ou TRANSCRICAO)
            parts = content.split(marker_metadata)
            meta_block = parts[1]
            
            # Descobre onde termina o bloco de metadados
            end_markers = [marker_summary, marker_transcription]
            min_idx = len(meta_block)
            for m in end_markers:
                idx = meta_block.find(m)
                if idx != -1 and idx < min_idx:
                    min_idx = idx
            
            meta_text = meta_block[:min_idx].strip()
            # Store the full block for output
            full_metadata_str = f"{marker_metadata}\n{meta_text}"
            
            # Parse linhas
            for line in meta_text.split('\n'):
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip().upper()] = val.strip()
        except Exception as e:
            print(f"  ! Erro ao extrair metadados de {filename}: {e}")

    # 1. Extração da Transcrição
    if marker_transcription in content:
        parts = content.split(marker_transcription)
        clean_text = parts[1].strip()
        
        # 2. Extração do Resumo (se houver metadados antes da transcrição)
        pre_transcription = parts[0]
        if marker_summary in pre_transcription:
            # Pega o que está entre o marcador de resumo e o final do bloco
            summary_part = pre_transcription.split(marker_summary)[1].strip()
            # Se houver metadados antes do resumo, o split anterior pegou tudo. 
            # Mas como split(marker_summary) pega o que vem APÓS, isola do metadata.
            summary_text = summary_part
            
            # Hack: Se o summary_text contiver o marcador de transcrição (não deveria, pois usamos pre_transcription), ok.
            # Mas se contiver metadados (caso a ordem fosse diferente), precisaríamos limpar. 
            # Assumindo ordem: Metadata -> Resumo -> Transcrição
    else:
        # Fallback para arquivos antigos ou sem formato definido
        raw_text = content.strip()
        
        if filename.lower().endswith('.srt'):
            clean_text = clean_srt_content(raw_text)
        else:
            # Remove timestamps de SRT se ainda existirem (modo legados .txt)
            clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', raw_text)
            
        summary_text = "Resumo não encontrado no arquivo original."
    
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    full_text = ' '.join(lines)
    
    # Formatação do Cabeçalho e Metadados
    json_meta = get_metadata(full_path)
    
    data_str = metadata.get("DATA") or json_meta["date"]
    titulo_str = metadata.get("TÍTULO") or json_meta["title"]
    id_str = metadata.get("ID") or json_meta["id"]

    if len(data_str) == 8 and data_str.isdigit():
        data_str = f"{data_str[:4]}-{data_str[4:6]}-{data_str[6:]}"
        
    header = (
        f"\n--- METADADOS DO DOCUMENTO ---\n"
        f"DATA: {data_str}\n"
        f"TÍTULO: {titulo_str}\n"
        f"ID: {id_str}\n"
        f"ARQUIVO: {filename}\n"
        f"-------------------------------\n\n"
        f"--- TRANSCRICAO COMPLETA ---\n"
    )
    
    footer = f"\n\n{'='*30}\nFIM DO VÍDEO: {filename}\n{'='*30}\n"
    
    return header + full_text + footer, full_text, summary_text

def save_volume(channel, volume, content):
    """
    Função principal:
    Realiza o parse literal string->disco e cria um arquivo .txt formatado 
    com o prefixo "CONSOLIDADO_[Canal]_VOL_XXX.txt" apontando para a pasta output 'volumes_notebooklm'.
    """
    output_dir = "volumes_notebooklm"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_name = os.path.join(output_dir, f"CONSOLIDADO_{channel}_VOL_{volume:03d}.txt")
    with open(output_name, 'w', encoding='utf-8') as out:
        out.write(f"CANAL: {channel} | VOLUME: {volume}\n")
        out.write(f"--- CONTEÚDO DOS VÍDEOS ---\n")
        out.write(content)
    print(f"✓ Arquivo gerado: {output_name}")

def process_channel(channel_path, channel_name):
    """
    Função principal:
    Agrupa vídeos soltos e consolida seus textos lado a lado iterativamente
    como uma fita cassete. Uma vez que o payload em texto acumulado estourar MAX_CHARS (ex: +1.8MB),
    o limite é acionado para cortar o volume, persistí-lo para .txt na subpasta designada, e reiniciar a esteira volumétrica com ID+1.
    """
    current_content = ""
    volume = 1
    
    # Valida estrutura de nomenclaturas do Youtube do canal selecionado em seu escopo de arquivos no diretório:
    # Match Regex exige o padrão de prefixo: "[NOME DO CANAL]-[ID DE 11 CARACTERES].extensão"
    pattern = re.compile(rf"^{re.escape(channel_name)}-[A-Za-z0-9_-]{{11}}(?:-[a-zA-Z0-9-]+)?\.(txt|srt)$")
    
    files = [f for f in os.listdir(channel_path) 
             if pattern.match(f) and not f.startswith("CONSOLIDADO_")]
    if not files:
        return

    # Sort files to ensure deterministic order (optional but good practice)
    files.sort()
    
    print(f"--- Processando Canal: {channel_name} ---")

    for f in files:
        full_path = os.path.join(channel_path, f)
        with open(full_path, 'r', encoding='utf-8') as file:
            processed, _, _ = process_content(file.read(), f, full_path)
            
            # 1. Verifica se adicionar este arquivo fará o volume estourar o limite
            # (e garante que current_content não está vazio, para um arquivo muito grande não causar erro)
            if len(current_content) > 0 and (len(current_content) + len(processed)) > MAX_CHARS:
                print(f"  ! Arquivo fará o Volume {volume} atingir o limite. Salvando o volume atual...")
                
                save_volume(channel_name, volume, current_content)
                
                volume += 1
                current_content = ""
            
            # 2. Adiciona o conteúdo do arquivo com segurança no volume apropriado
            current_content += processed
            print(f"  > Adicionado: {f}")

    # Salva o último volume (ou o único)
    if current_content:
        save_volume(channel_name, volume, current_content)
        # pending_archive block removed

def consolidate_by_channel(base_path):
    """
    Função principal:
    Entry-point do lexis-join que varre recursivamente a pasta base buscando
    vídeos na raiz que compõe um canal base, para então chamar subdiretórios 
    (assumindo diretório/pasta = nome de canal distinto) acionando a função iteradora process_channel(subpasta).
    """
    # 1. Busca vídeos avulsos espalhados no diretório . atual.
    base_files = [f for f in os.listdir(base_path) 
                  if f.endswith(('.txt', '.srt')) and not f.startswith("CONSOLIDADO_")]
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