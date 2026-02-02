import os
import boto3
import shutil
import sqlite3
import zipfile
import wave
import pandas as pd
from pathlib import Path
from PIL import Image
from langchain_core.tools import tool
from langchain_unstructured import UnstructuredLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# AWS Global Config
s3 = boto3.client('s3')
BUCKET = "sorterra-group-data-2026"
VECTOR_DB_PATH = "/tmp/sorterra_memory" # Ephemeral memory for container session
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
MAX_CHARS = 8000 

class SorterraMemory:
    def __init__(self):
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        self.db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=EMBEDDING_MODEL)

    def get_similar_mapping(self, content: str):
        try:
            results = self.db.similarity_search_with_score(content, k=5)
            confident_results = [r for r in results if r[1] < 0.6]
            if not confident_results: return "No high-confidence matches in memory."
            return "\n".join([f"Previously sorted to '{d.metadata.get('destination')}'" for d, s in confident_results])
        except Exception: return "Memory error."

    def learn_new_move(self, content: str, destination: str):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(content)
        metadatas = [{"destination": destination} for _ in chunks]
        self.db.add_texts(texts=chunks, metadatas=metadatas)

memory = SorterraMemory()

@tool
def read_file_content(file_key: str):
    """Downloads S3 file and extracts content from 23+ formats."""
    local_path = Path(f"/tmp/{os.path.basename(file_key)}")
    try:
        s3.download_file(BUCKET, file_key, str(local_path))
        ext = local_path.suffix.lower().strip('.')
        
        # Preserve your specific handlers
        if ext in ['json', 'txt', 'md', 'log']:
            with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f"[{ext.upper()}]: {f.read(MAX_CHARS)}"
        elif ext == 'csv':
            return f"[CSV Sample]:\n{pd.read_csv(local_path, nrows=5).to_string()}"
        elif ext == 'sqlite':
            conn = sqlite3.connect(local_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]
            conn.close()
            return f"[SQLite Tables]: {', '.join(tables)}"
        
        # General Document Handler
        loader = UnstructuredLoader(str(local_path), strategy="fast")
        docs = loader.load()
        return "\n\n".join([d.page_content for d in docs])[:MAX_CHARS]
    finally:
        if local_path.exists(): os.remove(local_path)

@tool
def move_file(source_key: str, destination_folder: str):
    """Moves S3 object with unique naming logic and memory indexing."""
    filename = os.path.basename(source_key)
    target_key = f"sorted/{destination_folder}/{filename}"
    
    # Preserve your 'uniqueness' logic for S3
    counter = 1
    while True:
        try:
            s3.head_object(Bucket=BUCKET, Key=target_key)
            name, ext = os.path.splitext(filename)
            target_key = f"sorted/{destination_folder}/{name}_{counter}{ext}"
            counter += 1
        except: break # Key doesn't exist, we can use it

    content = read_file_content.invoke(source_key)
    s3.copy_object(Bucket=BUCKET, CopySource={'Bucket': BUCKET, 'Key': source_key}, Key=target_key)
    s3.delete_object(Bucket=BUCKET, Key=source_key)
    
    if "Error" not in content:
        memory.learn_new_move(content, destination_folder)
    return f"Moved to {target_key}"

@tool
def rename_file(source_key: str, new_name: str):
    """Renames an S3 object (Copy + Delete)."""
    target_key = f"{os.path.dirname(source_key)}/{new_name}"
    s3.copy_object(Bucket=BUCKET, CopySource={'Bucket': BUCKET, 'Key': source_key}, Key=target_key)
    s3.delete_object(Bucket=BUCKET, Key=source_key)
    return f"Renamed to {new_name}"

@tool
def list_s3_contents(prefix: str):
    """Lists files or 'folders' in S3."""
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, Delimiter='/')
    files = [obj['Key'] for obj in response.get('Contents', [])]
    folders = [pref['Prefix'] for pref in response.get('CommonPrefixes', [])]
    return {"files": files, "folders": folders}

TOOLS = [move_file, read_file_content, rename_file, list_s3_contents]