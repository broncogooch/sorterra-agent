import os
from typing import Literal
from pathlib import Path
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from core.schema import AgentState
from core.tools import TOOLS, RLM_TOOLS, read_file_content, memory, repl_engine

load_dotenv()

# --- Model Definitions (Updated for 2026 API) ---
# Sonnet 4.5 is the current gold standard for agentic reasoning
sonnet = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0)
model_with_tools = sonnet.bind_tools(TOOLS)

# --- Recursive Sub-Agent Definition ---
# Wrapping this in a SystemMessage for better instruction persistence
RLM_SYSTEM_PROMPT = SystemMessage(content=(
    "You are an Extraction Specialist using a Recursive Language Model approach. "
    "You have access to a 'context' variable in the python_repl containing document text.\n\n"
    "STRATEGY:\n"
    "1. Analyze the 'context' length using python_repl.\n"
    "2. If it is large, use python_repl to chunk it (e.g., re.split by double newlines).\n"
    "3. Use haiku_query to summarize each chunk into a list of strings.\n"
    "4. Finally, synthesize all chunks into: Document Type, Project Identifiers, "
    "Key Entities, and a 2-sentence overview."
))

# Instantiating the internal agent with the correct 'prompt' parameter
analysis_sub_agent = create_react_agent(
    model=sonnet,
    tools=RLM_TOOLS,
    prompt=RLM_SYSTEM_PROMPT
)

def analyzer_node(state: AgentState):
    """Uses a recursive sub-agent to handle deep-analysis of large files."""
    file_path = state["current_file"]
    full_content = read_file_content.invoke(file_path)
    
    # Pre-load the content into the shared REPL engine
    repl_engine.globals["context"] = full_content
    
    # Run recursive agent with a 25-turn safety limit
    recursive_result = analysis_sub_agent.invoke(
        {"messages": [HumanMessage(content=f"Deep-analyze file: {Path(file_path).name}")]},
        config={"recursion_limit": 25} 
    )
    
    last_msg = recursive_result["messages"][-1]
    file_summary = last_msg.content
    
    # Log token usage for cost tracking
    usage = getattr(last_msg, 'usage_metadata', {})
    print(f"📊 Recursive analysis consumed {usage.get('total_tokens', '???')} tokens.")

    past_hints = memory.get_similar_mapping(full_content)
    
    analysis = (
        f"FILE: {Path(file_path).name}\n"
        f"EXTRACTED METADATA:\n{file_summary}\n\n"
        f"PAST ACTIONS (MEMORY):\n{past_hints}"
    )
    return {"analysis_summary": analysis}

# --- Main Sorting Logic ---
def sorting_agent(state: AgentState):
    rules_str = "\n".join(state["recipe"]["rules"])
    system_prompt = SystemMessage(content=(
        f"You are Sorterra. Organize the file based on Rules and Analysis.\n\n"
        f"RULES:\n{rules_str}\n\n"
        f"ANALYSIS:\n{state['analysis_summary']}"
    ))
    response = model_with_tools.invoke([system_prompt] + state['messages'])
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