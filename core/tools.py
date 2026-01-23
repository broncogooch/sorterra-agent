import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from langchain_unstructured import UnstructuredLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
# --- RLM Support Components ---
# The "Mini" model for recursive sub-calls
haiku = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
# The shared REPL environment for the recursive process
repl_engine = PythonREPL()

@tool
def haiku_query(task: str, text_chunk: str):
    """
    Recursive Tool: Queries a fast sub-model to process a specific chunk of text.
    Use this for summarizing parts of a large document.
    """
    prompt = f"TASK: {task}\n\nCONTENT:\n{text_chunk}"
    return haiku.invoke(prompt).content

@tool
def python_repl(code: str):
    """
    Recursive Tool: Executes Python code to manipulate the 'context' variable.
    Use this to chunk text using regex or extract specific ranges (e.g., context[:5000]).
    """
    return repl_engine.run(code)

# --- Original Sorterra Tools ---
VECTOR_DB_PATH = "./data/sorterra_memory"
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
BASE_SORTED_DIR = Path("data/sorted_data")

class SorterraMemory:
    def __init__(self):
        self.db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=EMBEDDING_MODEL)

    def get_similar_mapping(self, content: str):
        try:
            results = self.db.similarity_search_with_score(content, k=5)
            confident_results = [r for r in results if r[1] < 0.6]
            if not confident_results: return "No high-confidence matches."
            return "\n".join([f"Sorted to '{d.metadata.get('destination')}'" for d, s in confident_results])
        except: return "Memory access error."

    def learn_new_move(self, content: str, destination: str):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(content)
        metadatas = [{"destination": destination} for _ in chunks]
        self.db.add_texts(texts=chunks, metadatas=metadatas)

memory = SorterraMemory()

@tool
def read_file_content(file_path: str):
    """Extracts text content from various file formats."""
    path = Path(file_path)
    if not path.exists(): return f"Error: {file_path} not found."
    try:
        loader = UnstructuredLoader(str(path), mode="elements", strategy="fast")
        return "\n\n".join([d.page_content for d in loader.load()])
    except Exception as e: return f"Error: {str(e)}"

@tool
def move_file(source_path: str, destination_folder: str):
    """Moves file to sorted_data and teaches memory."""
    source = Path(source_path)
    dest_dir = BASE_SORTED_DIR / destination_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name
    try:
        content = read_file_content.invoke(source_path)
        shutil.move(str(source), str(target))
        memory.learn_new_move(content, destination_folder)
        return f"Moved to {target}."
    except Exception as e: return f"Failed: {str(e)}"

@tool
def list_local_files(directory: str):
    """Lists files in a directory."""
    path = Path(directory)
    return [str(f) for f in path.iterdir() if f.is_file()] if path.is_dir() else "Error."

@tool
def rename_file(source_path: str, new_name: str):
    """Renames a file."""
    source = Path(source_path)
    try:
        source.rename(source.parent / new_name)
        return f"Renamed to {new_name}."
    except: return "Failed."

TOOLS = [move_file, list_local_files, read_file_content, rename_file]
RLM_TOOLS = [python_repl, haiku_query]