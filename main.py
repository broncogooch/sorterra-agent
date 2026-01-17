from core.agent import app
from core.tools import list_local_files
from langchain_core.messages import HumanMessage

TEST_FOLDER = "./data/test_folder"
DEFAULT_RECIPE = {
    "name": "Project Sort",
    "rules": [
        "1. If file is an invoice, move to 'Finance/Invoices'.",
        "2. If it mentions a Project (e.g. Alpha), move to 'Projects/[Name]'.",
        "3. Otherwise, 'Unsorted'.",
        "4. Prioritize simple and meaningul file names"
    ]
}

if __name__ == "__main__":
    files = list_local_files.invoke(TEST_FOLDER)
    
    for file_path in files:
        print(f"\n>>> PROCESSING: {file_path}")
        inputs = {
            "messages": [HumanMessage(content=f"Sort this file: {file_path}")],
            "recipe": DEFAULT_RECIPE,
            "current_file": file_path
        }
        
        for output in app.stream(inputs, stream_mode="updates"):
            for node, values in output.items():
                # Node Completion Marker (Quiet)
                if node == "analyzer":
                    print(f"Analysis Complete.")
                
                # Log actual tool execution results
                if node == "tools" and "messages" in values:
                    last_msg = values["messages"][-1]
                    print(f"RESULT: {last_msg.content}")

        print(f"--- Finished ---\n")