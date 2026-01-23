from pathlib import Path
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
        print(f"\n>>> 🔍 STARTING DEEP ANALYSIS: {file_path}")
        inputs = {
            "messages": [HumanMessage(content=f"Sort this file: {file_path}")],
            "recipe": DEFAULT_RECIPE,
            "current_file": file_path
        }
        
        # Using stream_mode="values" or "updates" works great here
        for output in app.stream(inputs, stream_mode="updates"):
            for node, values in output.items():
                if node == "analyzer":
                    # This only triggers AFTER the recursive sub-agent finishes its iterations
                    print(f"✅ Context Analyzed (Recursive Logic Complete)")
                
                if node == "tools":
                    # This captures the FINAL sorting actions (move/rename)
                    last_msg = values["messages"][-1]
                    # Check the AIMessage's usage_metadata for total tokens
                    if hasattr(last_msg, 'usage_metadata'):
                         tokens = last_msg.usage_metadata.get('total_tokens', 'N/A')
                         print(f"📈 Step Tokens: {tokens}")
                    
                    print(f"🛠️ ACTION RESULT: {last_msg.content}")

        print(f"--- Finished {Path(file_path).name} ---\n")