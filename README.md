# Sorterra Agent 

**Sorterra** is an intelligent, agentic file management system developed as a capstone project for the BYU MISM program. It leverages LLMs and RAG (Retrieval-Augmented Generation) to autonomously sort documents into a clean, hierarchical structure based on content analysis and historical memory.

---

## Architecture

Sorterra uses a **LangGraph** state machine to handle complex sorting logic:

1. **Analyzer Node**  
   Distills raw file content (PDF, DOCX, TXT) and retrieves *Memory Hints* from a Chroma vector store.

2. **Agent Node**  
   A reasoning engine (**Claude 3.5 Sonnet**) that applies user-defined recipes to the analysis.

3. **Tool Node**  
   Executes the physical file move and indexes the successful action into vector memory for future “learning”.

---

## Project Structure

```text
SORTERRA-AGENT/
├── core/                # Core Agent Logic
│   ├── agent.py         # LangGraph definition
│   ├── schema.py        # State & Type definitions
│   └── tools.py         # File system & Vector DB tools
├── data/                # Local data (Git ignored)
│   ├── test_folder/     # Input for sorting
│   └── sorted_data/     # Structured output
├── main.py              # System entry point
├── .env                 # API Keys (Anthropic)
└── requirements.txt     # Dependencies
```

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```
### 2. Setup Environment
Create a .env file with your Anthropic API key:

`ANTHROPIC_API_KEY=your_sk_key_here`

### 3. Run the Agent
Place files in `data/test_folder/` and run:

```bash
python main.py
```
Tech Stack
Orchestration: LangGraph / LangChain

LLM: Anthropic Claude 3.5 Sonnet

Vector DB: ChromaDB

Embeddings: HuggingFace (sentence-transformers)