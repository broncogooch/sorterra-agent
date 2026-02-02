import os
from pathlib import Path
from dotenv import load_dotenv
# Note: Ensure you have installed the additional requirements: 
# pip install Pillow reportlab openpyxl python-pptx python-docx pandas pyarrow

# Import the generation logic from your new script
# (Assuming the logic from generate_files.py is accessible)
from utils.generate_files import FILE_GENERATORS, random_filename

def generate_sorterra_test_data(num_files=15, max_size_mb=1):
    """
    Generates a diverse set of random files in the Sorterra test directory.
    """
    load_dotenv()
    # Direct output to Sorterra's expected input folder
    output_path = Path("./data/test_folder")
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"--- Generating {num_files} Diverse Test Files ---")
    
    for i in range(num_files):
        import random
        file_type = random.choice(list(FILE_GENERATORS.keys()))
        filename = f"{random_filename()}.{file_type}"
        filepath = output_path / filename
        
        try:
            generator = FILE_GENERATORS[file_type]
            generator(str(filepath), max_size_mb)
            print(f"[{i+1}/{num_files}] Created: {filename}")
        except Exception as e:
            print(f"Error generating {filename}: {e}")

if __name__ == "__main__":
    generate_sorterra_test_data()