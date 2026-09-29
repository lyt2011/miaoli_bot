"""
后续换成自动发现
这里迟早要迁移的
我想快速看到成果
所以先在这瞎写吧
"""

from typing						import Any, Dict, Optional
from langchain_core.messages	import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime			import Runtime
from langgraph.prebuilt			import ToolNode

from ..models	import GraphRuntimeContext, GraphState

import json


async def format_input(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	humen_message = json.dumps({
		"event"		: state["event"],
		"segments"	: state["segments"]
	}, indent=2, ensure_ascii=False)
	
	return {"messages": [HumanMessage(humen_message)]}

async def format_prompt(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	cfg		= runtime.context["plugin_config"]
	account	= cfg.account_config
	
	account_info = "\n".join([
		"<account>",
		f"Administrator QQ number: {account.root_id}",
		f"Administrator nickname: {account.root_nickname}",
		f"Bot QQ number: {account.bot_id}",
		f"Bot nickname: {account.bot_nickname}",
		"</account>"
	])
	
	return {"system_prompt": "\n".join([account_info, cfg.system_prompt])}

async def call_llm(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	chat_model		= runtime.context["chat_model"].bind_tools(runtime.context["tools"])
	message			= [SystemMessage(state["system_prompt"]), *state["messages"]]
	assistant_msg	= await chat_model.ainvoke(message)
	
	return {"messages": [assistant_msg]}

async def on_tool_calling(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	if "tools" not in runtime.context:
		return None
		
	return await ToolNode(runtime.context["tools"]).ainvoke({"messages": state["messages"]})

async def last_msg_to_answer(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	last_message = state["messages"][-1]
	return {"final_answer": last_message.content if isinstance(last_message, AIMessage) else "我就是Bug."}
