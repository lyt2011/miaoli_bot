from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.stores	import SHARE_STORE

from typing						import Any, Dict, Optional
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import HumanMessage, ToolMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import is_target_model


async def fix_tool_attachment(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""修复附件在工具结果中导致400的问题"""
	
	plugin_cfg	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	provider	= state.get("provider", "null")
	model		= state.get("model", "null")
	
	# 未命中不继续
	if not is_target_model(provider=provider, model=model):
		return None
	
	# 新上下文与处理中的附件
	replaced	= []
	pending		= []
	is_changed	= False
	
	for message in state.get("messages", []):
		
		# 非 ToolMessage 时 flush
		if not isinstance(message, ToolMessage):
			
			if pending:
				replaced.extend(pending)
				pending.clear()
			
			replaced.append(message)
		
		# 字符串类型的 ToolMessage 直接跳过
		elif isinstance(message.content, str):
			replaced.append(message)
		
		# 非字符串 ToolMessage 作为处理目标
		else:
			
			raw_content		= list(message.content)
			message.content	= plugin_cfg.replace_text
			
			replaced.append(message)
			pending.append(HumanMessage(raw_content, id=f"image-{message.tool_call_id}"))
			
			if not is_changed:
				is_changed = True
	
	# 兜底
	if pending:
		replaced.extend(pending)
	
	return {"messages": Overwrite(replaced)} if is_changed else None
