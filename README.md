# Lexis - Processamento de Legendas com IA

**Objetivo**: Preparar e consolidar transcrições de vídeos do YouTube para estudo e RAG (Retrieval-Augmented Generation) no NotebookLM, sem perder informações.

## Ferramentas

### 1. `lexis.py` (Online 🌐)
Processa arquivos `.srt` individualmente usando a IA do Google Gemini.

**Funcionalidades:**
- ✨ **Resumo via IA**: Gera um resumo executivo focado em conceitos-chave.
- 🧹 **Limpeza Inteligente**: Remove timestamps e formatação, mantendo o texto limpo.
- 🎨 **Interface Rica**: Saída colorida no terminal para fácil acompanhamento.
- 🔒 **Segurança**:
    - **Processamento em Lote**: Processa todos os arquivos primeiro.
    - **Arquivamento Seguro**: Move os `.srt` originais para a pasta `archive` **apenas se** o processamento for bem-sucedido e o arquivo `.txt` final existir.
- 🤖 **Metadados**: Tenta extrair ID e Título de arquivos `.info.json` (se existirem).

### 2. `lexis-join.py` (Offline ⚡)
Consolida múltiplos arquivos `.txt` (gerados pelo `lexis.py`) em "volumes" grandes.

**Funcionalidades:**
- 🚀 **100% Offline**: Não consome API nem requer internet. Reutiliza os resumos já gerados pelo `lexis.py`.
- 📚 **Volumes Inteligentes**: Agrupa vídeos até atingir ~2MB (ponto ideal para LLMs).
- 🧠 **Coletânea de Resumos**: O cabeçalho de cada volume contém todos os resumos dos vídeos incluídos nele.
- 🛡️ **Integridade**: Garante que um vídeo nunca seja dividido pela metade entre dois volumes.
- 📂 **Preservação**: Não move nem apaga seus arquivos `.txt` originais.

## Configuração

### Pré-requisitos
- Python 3.8+
- Chave de API do Google Gemini (Apenas para o `lexis.py`)

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

### Configuração da API
Para usar o `lexis.py`, você precisa de uma API Key do Google Gemini.
O script procura automaticamente por um arquivo `.env` **na mesma pasta do script**.

1. Crie um arquivo chamado `.env` dentro da pasta `lexis/`.
2. Adicione sua chave nele:
   ```env
   GEMINI_API_KEY=sua_chave_aqui_xyz
   ```

## Uso

### Passo 1: Processar Legendas (`lexis.py`)
Navegue até a pasta onde estão seus arquivos `.srt` e rode:

```bash
python /caminho/para/lexis.py
```

O script irá:
1. Encontrar todos os `.srt`.
2. Gerar `.txt` com Resumo + Transcrição.
3. Mover os `.srt` processados para uma pasta `archive/`.

### Passo 2: Consolidar Volumes (`lexis-join.py`)
Para juntar os textos em grandes volumes para o NotebookLM:

```bash
python /caminho/para/lexis-join.py
```

O script irá:
1. Varrer a pasta atual e subpastas.
2. Criar arquivos `CONSOLIDADO_NomeDoCanal_VOL_001.txt`, `VOL_002.txt`, etc.
3. Manter seus arquivos `.txt` originais intactos.

## Estrutura de Arquivos

```
.
├── .env                  # Sua chave de API
├── requirements.txt      # Dependências
├── lexis.py              # Script de processamento (IA)
├── lexis-join.py         # Script de consolidação (Offline)
└── (Pasta dos Vídeos)
    ├── video1.srt
    ├── video1.info.json
    ├── video1.txt        # Gerado pelo lexis
    └── archive/          # Onde ficam os .srt originais
        └── video1.srt
```
