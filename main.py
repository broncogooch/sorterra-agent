from core.agent import app
from core.tools import list_local_files
from langchain_core.messages import HumanMessage

TEST_FOLDER = "./data/test_folder"
DEFAULT_RECIPE = {
    "name": "ACME Corp Enterprise Sort",
    "rules": [
        "1. If a file is an invoice or mentions a vendor (e.g., AWS, Stripe), move to 'Finance/Invoices/[VendorName]'.",
        "2. If it mentions a specific Project (Alpha, Beta, Phoenix, etc.), move to 'Projects/[ProjectName]'.",
        "3. If it is related to a specific department (HR, Marketing, Engineering) but not a project, move to 'Departments/[DepartmentName]'.",
        "4. If it is a technical document (Technical Spec, Audit Report, SQL Database), move to 'Engineering/Technical'.",
        "5. If it is a personal or miscellaneous item (like a Grocery List), move to 'Personal/Unsorted'.",
        "6. Always rename files to a clean 'DocumentType_Project_Date' format if they are currently messy."
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