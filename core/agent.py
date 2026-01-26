from typing import Literal
from langchain_anthropic import ChatAnthropic
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from core.schema import AgentState
from core.tools import TOOLS, read_file_content, memory

load_dotenv()
# Initialize model
model_thinking = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0).bind_tools(TOOLS)
model_quick = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

def analyzer_node(state: AgentState):
    """Summarizes full file content and fetches memory hints."""
    file_path = state["current_file"]
    full_content = read_file_content.invoke(file_path)
    
    summary_prompt = (
        "Analyze the following document and extract key metadata for an automated sorting system. "
        "Focus on these specific points:\n"
        "1. Document Type: (e.g., Invoice, Project Plan, Meeting Notes, Personal List)\n"
        "2. Project Identifiers: (Any mention of project names like 'Alpha', 'Beta', etc.)\n"
        "3. Key Entities: (Company names, vendors, or individuals mentioned)\n"
        "4. Brief Overview: A concise 2-sentence summary of the document's purpose.\n\n"
        f"CONTENT:\n{full_content}"
    )
    
    file_summary = model_quick.invoke([HumanMessage(content=summary_prompt)]).content
    past_hints = memory.get_similar_mapping(full_content)
    
    analysis = (
        f"FILE: {Path(file_path).name}\n"
        f"EXTRACTED METADATA:\n{file_summary}\n\n"
        f"MEMORY HINTS (PAST ACTIONS):\n{past_hints}"
    )
    
    return {"analysis_summary": analysis}

def sorting_agent(state: AgentState):
    """Decides the move based on the analysis summary."""
    rules_str = "\n".join(state["recipe"]["rules"])
    
    system_prompt_content = (
        "You are Sorterra, an expert file organization assistant. Your objective is to organize "
        "the current file based on the 'Sorting Rules' and the 'Analysis Summary' provided.\n\n"
        "### Operational Workflow:\n"
        "1. **Sanitize Filename**: Examine the current filename. If it contains random suffixes "
        "(e.g., '_vsj0') or is otherwise messy, use 'rename_file' to give it a clean, professional name.\n"
        "2. **Apply Rules**: Use 'move_file' to categorize the file based strictly on the provided Rules.\n"
        "3. **Check Memory**: Use 'MEMORY HINTS' to ensure consistency with past decisions, but "
        "always prioritize the specific Rules if they conflict.\n\n"
        f"### Sorting Rules:\n{rules_str}\n\n"
        f"### Current Analysis:\n{state['analysis_summary']}\n\n"
        "Decision Task: Choose the most appropriate action(s) to fulfill the sorting request."
    )
    
    system_prompt = SystemMessage(content=system_prompt_content)
    response = model_thinking.invoke([system_prompt] + state['messages'])

    # LOGGING: Only print if there's a specific tool action or a final conclusion
    if response.tool_calls:
        for tool_call in response.tool_calls:
            # Clean logging for tool selection
            args = tool_call['args']
            action_desc = f"{tool_call['name']}({', '.join([f'{k}={v}' for k, v in args.items()])})"
            print(f"ACTION: {action_desc}")
    else:
        # Final reasoning summary
        print(f"REASONING: {response.content.strip()}")

    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    return "tools" if state['messages'][-1].tool_calls else "__end__"

# Graph Construction
workflow = StateGraph(AgentState)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("agent", sorting_agent)
workflow.add_node("tools", ToolNode(TOOLS))

workflow.set_entry_point("analyzer")
workflow.add_edge("analyzer", "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app = workflow.compile()