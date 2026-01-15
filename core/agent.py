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
model = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0).bind_tools(TOOLS)

def analyzer_node(state: AgentState):
    """distills raw file data and memory into a clean summary."""
    file_path = state["current_file"]
    content = read_file_content.invoke(file_path)
    past_hints = memory.get_similar_mapping(content)
    
    summary = f"FILE: {Path(file_path).name}\nPREVIEW: {content[:400]}...\nMEMORY HINTS: {past_hints}"
    return {"analysis_summary": summary}

def sorting_agent(state: AgentState):
    """Decides the move based on the analysis summary."""
    rules_str = "\n".join(state["recipe"]["rules"])
    system_prompt = SystemMessage(content=(
        f"You are the Sorterra Agent. Rules:\n{rules_str}\n\n"
        f"CURRENT ANALYSIS:\n{state['analysis_summary']}\n\n"
        "Decision Task: Use 'move_file' based on the Rules and Analysis Summary."
    ))
    response = model.invoke([system_prompt] + state['messages'])
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