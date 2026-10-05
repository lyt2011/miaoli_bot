from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.stores	import SHARE_STORE

from typing						import Any, Dict, Optional
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import HumanMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import is_target_message, is_target_model

async def fix_tool_attachment(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""修复附件在工具结果中导致400的问题"""
	
	plugin_cfg	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider	= state.get("provider_name", "null")
	model		= state.get("model_name", "null")
	messages	= state.get("messages", [])
	
	# 未命中不继续
	if not is_target_model(provider=provider, model=model):
		return None
	
	replaced	= []
	is_changed	= False
	
	for message in messages:
		
		if not is_target_message(message):
			replaced.append(message)
			continue
		
		tc_id			= message.tool_call_id
		tool_output		= list(message.content)
		message.content	= plugin_cfg.replace_text
		
		replaced.append(message)
		replaced.append(HumanMessage(tool_output, id=f"image-{tc_id}"))
		
		# 改变 is_changed 标志位
		if not is_changed:
			is_changed = True
	
	return {"messages": Overwrite(replaced)} if is_changed else None
