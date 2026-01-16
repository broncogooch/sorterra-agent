from core.agent import app
from core.tools import list_local_files
from langchain_core.messages import HumanMessage

TEST_FOLDER = "./data/test_folder"
DEFAULT_RECIPE = {
    "name": "Project Sort",
    "rules": [
        "1. If file is an invoice, move to 'Finance/Invoices'.",
        "2. If it mentions a Project (e.g. Alpha), move to 'Projects/[Name]'.",
        "3. Otherwise, 'Unsorted'."
    ]
}

if __name__ == "__main__":
    files = list_local_files.invoke(TEST_FOLDER)
    
    for file_path in files:
        print(f"\n--- Processing: {file_path} ---")
        inputs = {
            "messages": [HumanMessage(content=f"Sort this file: {file_path}")],
            "recipe": DEFAULT_RECIPE,
            "current_file": file_path
        }
        
        for output in app.stream(inputs, stream_mode="updates"):
            for node, values in output.items():
                print(f"[{node}] step finished.")
        
                # Log specific results from the tools node
                if node == "tools" and "messages" in values:
                    last_msg = values["messages"][-1]
                    print(f"Tool Output: {last_msg.content}")