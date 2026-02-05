# Lexis - Processamento de Legendas com IA

Este projeto contém ferramentas para processar, resumir e consolidar legendas de vídeos (SRT) utilizando a API do Google Gemini.

## Ferramentas

### 1. `lexis.py`
Processa arquivos `.srt` individualmente.
- Gera um resumo executivo usando IA.
- Extrai metadados de arquivos `.info.json` (se existirem).
- Gera um arquivo `.txt` formatado contendo metadados, resumo e a transcrição limpa.

### 2. `lexis-join.py`
Consolida múltiplos arquivos `.srt` em "volumes" de texto.
- Útil para criar datasets grandes para RAG (Retrieval-Augmented Generation).
- Agrupa vídeos até atingir um limite de tamanho (configurável, padrão 2MB).
- Garante que vídeos não sejam divididos entre volumes.
- Gera um resumo do volume usando IA.

## Configuração

### Pré-requisitos
- Python 3.8+
- Chave de API do Google Gemini

### Instalação

1. Clone o repositório ou baixe os scripts.
2. Crie um ambiente virtual (recomendado):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Variável de Ambiente
Para utilizar os scripts, você **PRECISA** definir a variável de ambiente `GEMINI_API_KEY` com sua chave da API.

No terminal:
```bash
export GEMINI_API_KEY='sua_chave_aqui'
```

Para tornar permanente, adicione ao seu `~/.zshrc` ou `~/.bashrc`.

## Uso

### Processar arquivos individuais
Execute o script na pasta onde estão os arquivos `.srt`:
```bash
python lexis.py
```

### Consolidar legendas
Execute o script para gerar volumes consolidados:
```bash
python lexis-join.py
```
O script processará arquivos `.srt` na pasta atual e em subdiretórios.

## Estrutura de Arquivos Esperada
```
.
├── lexis.py
├── lexis-join.py
├── requirements.txt
├── .venv/
├── video1.srt
├── video1.info.json (opcional)
└── ...
```
