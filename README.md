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

- 🤖 **Metadados**: Tenta extrair ID e Título de arquivos `.info.json` (se existirem).

### 2. `lexis-chunk.py` (IA Structuring 🧠) 
**Novo!** Focado em estruturar o conteúdo para o NotebookLM.

**Funcionalidades:**
- 📝 **Chunking Inteligente**: Usa o modelo `gemini-2.0-flash` para reescrever a transcrição em blocos lógicos com Títulos e Subtítulos Markdown.
- 📐 **Estrutura Definida**: Transforma o texto corrido em um documento legível, ideal para RAG.
- 🏷️ **Metadados**: Cabeçalho rico com Data, Título e ID.

### 3. `lexis-join.py` (Offline ⚡)
Consolida múltiplos arquivos `.txt` e `.srt` em "volumes" grandes para o NotebookLM.

**Funcionalidades:**
- 🚀 **100% Offline**: Não consome API nem requer internet. Processa tanto legendas brutas (desduplicando-as) quanto transcrições geradas pelo `lexis.py`.
- 📚 **Volumes Inteligentes**: Agrupa vídeos agnósticamente até atingir ~1.8MB (ponto ideal de performance e janela de contexto estendida no NotebookLM).
- 🛡️ **Integridade e Metadados**: Garante que um vídeo nunca seja dividido pela metade entre dois volumes e acopla metadados originais (Data, Título, ID) puxados dos `.info.json`.
- 📂 **Preservação e Organização**: Mantém intactos os arquivos originais e salva todos os volumes prontos na pasta centralizadora `volumes_notebooklm/`.

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

## Uso

### Configuração do Alias (Recomendado)
Para facilitar o uso, crie um alias para o `lexis-chunk`:
1. Execute o script de ajuda:
   ```bash
   ./setup_alias.sh
   ```
2. Siga as instruções para adicionar ao seu `.zshrc`.

Depois, você pode rodar apenas:
```bash
lexis-chunk
```

### Passo 1: Processar Legendas (`lexis-chunk.py` ou `lexis.py`)
Navegue até a pasta onde estão seus arquivos `.srt` e rode:

```bash
python /caminho/para/lexis.py
```

O script irá:
1. Encontrar todos os `.srt`.
2. Gerar `.txt` com Resumo + Transcrição.
3. Mover os `.srt` processados para uma pasta `archive/`.

### Passo 2: Consolidar Volumes (`lexis-join.py`)
Para juntar os textos ou legendas cruas em grandes volumes otimizados para o NotebookLM:

```bash
python /caminho/para/lexis-join.py
```

O script irá:
1. Varrer a pasta atual e subpastas atrás de arquivos de vídeo/legenda.
2. Agrupar os textos mesclando metadados num grande pacote inteligente.
3. Criar arquivos `CONSOLIDADO_NomeDoCanal_VOL_001.txt`, `VOL_002.txt`, etc.
4. Salvar todos os volumes gerados na pasta de destino final `volumes_notebooklm/`.
5. Manter seus arquivos `.txt` e `.srt` originais intactos.

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
