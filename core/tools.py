import shutil
from pathlib import Path
from langchain_unstructured import UnstructuredLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import sqlite3
import json
import zipfile
import wave
from pathlib import Path
import pandas as pd
from PIL import Image
from langchain_unstructured import UnstructuredLoader
from langchain_core.tools import tool

VECTOR_DB_PATH = "./data/sorterra_memory"
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
BASE_SORTED_DIR = Path("data/sorted_data")
MAX_CHARS = 8000 

class SorterraMemory:
    def __init__(self):
        self.db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=EMBEDDING_MODEL, collection_metadata={"hnsw:space": "cosine"})

    def get_similar_mapping(self, content: str):
        try:
            # Use similarity_search_with_score instead
            results = self.db.similarity_search_with_score(content, k=5)
            
            # With cosine distance, 0 is a perfect match and higher numbers are further away.
            # Adjusted threshold: only keep matches with distance < 0.6
            confident_results = [r for r in results if r[1] < 0.6]
            
            if not confident_results:
                return "No high-confidence matches in memory."
                
            return "\n".join([f"Previously sorted to '{d.metadata.get('destination')}' (Dist: {s:.2f})" for d, s in confident_results])
        except Exception as e:
            return f"Memory access error: {str(e)}"

    def learn_new_move(self, content: str, destination: str):
        # Split text into manageable pieces
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100
        )
        chunks = text_splitter.split_text(content)
        
        # Store each chunk with the same destination metadata
        metadatas = [{"destination": destination} for _ in chunks]
        self.db.add_texts(texts=chunks, metadatas=metadatas)

memory = SorterraMemory()



@tool
def read_file_content(file_path: str):
    """
    Extracts text, schema, or metadata from 23+ file types (PDF, CSV, SQLite, Images, etc.).
    Optimized for efficiency and context window safety.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: {file_path} not found."

    ext = path.suffix.lower().strip('.')
    
    try:
        # 1. Specialized Handlers (Fast & Low Memory)
        if ext in ['json', 'yaml', 'yml', 'ini', 'log', 'txt', 'md']:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(MAX_CHARS)
                return f"[{ext.upper()} Content (truncated)]:\n{content}"
        
        elif ext == 'csv':
            df = pd.read_csv(path, nrows=10)
            return f"[CSV Sample]:\n{df.to_string()}"
            
        elif ext == 'sqlite':
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]
            conn.close()
            return f"[SQLite Database]: Found tables: {', '.join(tables)}"
            
        elif ext == 'parquet':
            df = pd.read_parquet(path)
            return f"[Parquet Schema]: Columns: {', '.join(df.columns)} | Rows: {len(df)}"
            
        elif ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
            with Image.open(path) as img:
                return f"[Image Metadata]: Format: {img.format}, Size: {img.size}, Mode: {img.mode}"
                
        elif ext == 'zip':
            with zipfile.ZipFile(path, 'r') as zf:
                return f"[ZIP Contents]: {', '.join(zf.namelist()[:20])}" # Limit to first 20 files
                
        elif ext == 'wav':
            with wave.open(str(path), 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
                return f"[Audio Metadata]: Duration: {duration:.2f}s, Channels: {wf.getnchannels()}"

        # 2. Document Fallback (PDF, DOCX, PPTX, XLSX, HTML, RTF)
        # Using "fast" strategy to avoid heavy OCR unless required
        loader = UnstructuredLoader(str(path), mode="elements", strategy="fast")
        docs = loader.load()
        full_text = "\n\n".join([d.page_content for d in docs])
        
        # 3. Context Window Management
        if len(full_text) > MAX_CHARS:
            # Head and Tail sampling: captures both the title/intro and any concluding info
            half = MAX_CHARS // 2
            return full_text[:half] + "\n\n[... content truncated ...]\n\n" + full_text[-half:]
        
        return full_text

    except Exception as e:
        return f"Error reading {path.name}: {str(e)}"

@tool
def move_file(source_path: str, destination_folder: str):
    """Moves file to the sorted_data directory without overwriting existing files."""
    source = Path(source_path)
    full_dest_dir = BASE_SORTED_DIR / destination_folder
    full_dest_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = full_dest_dir / source.name
    counter = 1
    while target_path.exists():
        # e.g., 'grocery_list.txt' -> 'grocery_list_1.txt'
        target_path = full_dest_dir / f"{source.stem}_{counter}{source.suffix}"
        counter += 1
    
    try:
        content = read_file_content.invoke(source_path)
        shutil.move(str(source), str(target_path)) # Uses unique target_path
        if "Error" not in content:
            memory.learn_new_move(content, destination_folder)
        return f"Moved {source.name} to {target_path}."
    except Exception as e:
        return f"Failed: {str(e)}"

@tool
def list_local_files(directory: str):
    """
    Lists all files currently residing in a specified local directory. 
    Use this tool to find files that need to be processed, renamed, or sorted.
    """
    path = Path(directory)
    return [str(f) for f in path.iterdir() if f.is_file()] if path.is_dir() else f"Error: {directory} not found."


@tool
def rename_file(source_path: str, new_name: str):
    """
    Changes the name of a file at a specific source_path to a provided new_name. 
    This is useful for cleaning up randomized or messy filenames (e.g., removing random suffixes) before organizing them.
    """
    source = Path(source_path)
    if not source.exists():
        return f"Error: {source_path} not found."
    try:
        new_path = source.parent / new_name
        source.rename(new_path)
        return f"Renamed to {new_name}."
    except Exception as e:
        return f"Failed: {str(e)}"


@tool
def list_folders(directory: str):
    """
    Lists all subdirectories within a specified local directory. 
    Use this tool to discover existing categories or project folders 
    (e.g., in 'data/sorted_data') to maintain organizational consistency.
    """
    path = Path(directory)
    if not path.exists():
        return f"Error: Directory {directory} not found."
    
    # Returns only folder names for cleaner LLM reasoning
    return [f.name for f in path.iterdir() if f.is_dir()]

# Update the TOOLS list to include the new tool
TOOLS = [move_file, list_local_files, read_file_content, rename_file, list_folders]