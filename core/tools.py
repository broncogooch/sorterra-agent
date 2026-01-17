import os
import shutil
from pathlib import Path
from langchain_unstructured import UnstructuredLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

VECTOR_DB_PATH = "./data/sorterra_memory"
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
BASE_SORTED_DIR = Path("data/sorted_data")

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
    Extracts text content from various file formats (PDF, DOCX, TXT, etc.) using Unstructured partitioning. 
    Use this tool to analyze the content of a file before determining its sorting destination.
    """
    path = Path(file_path)
    if not path.exists(): return f"Error: {file_path} not found."
    try:
        # Use UnstructuredLoader instead of UnstructuredFileLoader
        loader = UnstructuredLoader(str(path), mode="elements", strategy="fast")
        docs = loader.load()
        return "\n\n".join([d.page_content for d in docs])
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


TOOLS = [move_file, list_local_files, read_file_content, rename_file]