import os
import shutil
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

VECTOR_DB_PATH = "./data/sorterra_memory"
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
BASE_SORTED_DIR = Path("data/sorted_data")

class SorterraMemory:
    def __init__(self):
        self.db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=EMBEDDING_MODEL, collection_metadata={"hnsw:space": "cosine"})

    def get_similar_mapping(self, content: str):
        try:
            results = self.db.similarity_search_with_relevance_scores(content, k=2)
            if not results or results[0][1] < 0.4:
                return "No high-confidence matches in memory."
            return "\n".join([f"Previously sorted to '{d.metadata.get('destination')}' (Conf: {s:.2f})" for d, s in results])
        except:
            return "Memory is currently empty."

    def learn_new_move(self, content: str, destination: str):
        self.db.add_texts(texts=[content], metadatas=[{"destination": destination}])

memory = SorterraMemory()

@tool
def read_file_content(file_path: str):
    """Reads PDF, DOCX, or TXT content."""
    path = Path(file_path)
    if not path.exists(): return f"Error: {file_path} not found."
    try:
        loader = PyPDFLoader(str(path)) if path.suffix == ".pdf" else \
                 Docx2txtLoader(str(path)) if path.suffix == ".docx" else \
                 TextLoader(str(path))
        return " ".join([d.page_content for d in loader.load()])[:2000]
    except Exception as e:
        return f"Error reading {path.name}: {str(e)}"

@tool
def move_file(source_path: str, destination_folder: str):
    """Moves file to the sorted_data directory and updates vector memory."""
    source = Path(source_path)
    # Ensure all files end up inside 'sorted_data'
    full_dest_dir = BASE_SORTED_DIR / destination_folder
    full_dest_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        content = read_file_content.invoke(source_path)
        shutil.move(str(source), str(full_dest_dir / source.name))
        if "Error" not in content:
            memory.learn_new_move(content, destination_folder)
        return f"Moved {source.name} to {full_dest_dir}."
    except Exception as e:
        return f"Failed: {str(e)}"

@tool
def list_local_files(directory: str):
    """Lists files to be sorted."""
    path = Path(directory)
    return [str(f) for f in path.iterdir() if f.is_file()] if path.is_dir() else f"Error: {directory} not found."

TOOLS = [move_file, list_local_files, read_file_content]