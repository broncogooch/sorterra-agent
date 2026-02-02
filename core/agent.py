import time
import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from bedrock_agentcore import BedrockAgentCoreApp
from core.schema import AgentState
from core.tools import TOOLS, read_file_content, memory

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

app = BedrockAgentCoreApp()

# Create a custom config with 'adaptive' retries to handle throttling automatically
retry_config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'
    }
)

# Initialize a custom Bedrock client with the retry policy
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1', config=retry_config)

# Updated models to use the custom client and US Inference Profile IDs
model_thinking = ChatBedrockConverse(
    client=bedrock_runtime,
    model="us.meta.llama3-1-70b-instruct-v1:0", 
    temperature=0
).bind_tools(TOOLS)

model_quick = ChatBedrockConverse(
    client=bedrock_runtime,
    model="us.meta.llama3-1-8b-instruct-v1:0"
)

def analyzer_node(state: AgentState):
    file_key = state["current_file"]
    full_content = read_file_content.invoke(file_key)
    
    summary_prompt = f"Analyze document and extract metadata:\n\nCONTENT:\n{full_content}"
    file_summary = model_quick.invoke([HumanMessage(content=summary_prompt)]).content
    past_hints = memory.get_similar_mapping(full_content)
    
    return {"analysis_summary": f"METADATA:\n{file_summary}\n\nMEMORY:\n{past_hints}"}

def sorting_agent(state: AgentState):
    rules_str = "\n".join(state["recipe"]["rules"])
    system_prompt = SystemMessage(content=(
        f"You are Sorterra. Follow these rules:\n{rules_str}\n\n"
        f"Analysis:\n{state['analysis_summary']}"
    ))
    response = model_thinking.invoke([system_prompt] + state['messages'])
    return {"messages": [response]}

# Graph construction
workflow = StateGraph(AgentState)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("agent", sorting_agent)
workflow.add_node("tools", ToolNode(TOOLS))
workflow.set_entry_point("analyzer")
workflow.add_edge("analyzer", "agent")
workflow.add_conditional_edges("agent", lambda x: "tools" if x['messages'][-1].tool_calls else "__end__")
workflow.add_edge("tools", "agent")
workflow_app = workflow.compile()

@app.entrypoint
def invoke_sorterra(payload):
    file_key = payload['file_key']
    recipe = payload.get('recipe') or DEFAULT_RECIPE
    
    # Check if the file_key represents an S3 directory
    if file_key.endswith('/'):
        from core.tools import list_s3_contents
        contents = list_s3_contents.invoke(file_key)
        files_to_process = [f for f in contents.get('files', []) if f != file_key]
        
        batch_results = []
        for f in files_to_process:
            inputs = {
                "messages": [HumanMessage(content=f"Sort: {f}")],
                "recipe": recipe,
                "current_file": f
            }
            result = workflow_app.invoke(inputs)
            batch_results.append(f"{f}: {result['messages'][-1].content}")
            
            # Wait 10 seconds between files to respect low on-demand token quotas
            time.sleep(10)
        
        return {
            "status": "batch_complete",
            "processed_count": len(files_to_process),
            "result": "\n".join(batch_results)
        }
    
    # Standard single-file processing
    inputs = {
        "messages": [HumanMessage(content=f"Sort: {file_key}")],
        "recipe": recipe,
        "current_file": file_key
    }
    result = workflow_app.invoke(inputs)
    return {"status": "complete", "result": result["messages"][-1].content}

if __name__ == "__main__":
    app.run()