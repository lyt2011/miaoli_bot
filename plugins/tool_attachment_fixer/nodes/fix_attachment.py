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
	
	provider	= state.get("provider", "null")
	model		= state.get("model", "null")
	messages	= state.get("messages", [])
	
	# 未命中不继续
	if not is_target_model(provider=provider, model=model):
		return None
	
	# 新上下文与处理中的附件
	replaced	= []
	pending		= []
	is_changed	= False
	
	for message in messages:
		
		# 判断是否为修复目标 (ToolMessage)
		if not is_target_message(message):
			
			# 把结果倒出来 (因为此时 message 不是 ToolMessage)
			if pending:
				replaced.extend(pending)
				pending.clear()
			
			# 普通信息直接添加回去
			replaced.append(message)
			continue
		
		tc_id			= message.tool_call_id
		tool_output		= list(message.content)
		message.content	= plugin_cfg.replace_text
		
		# 改变工具输出后将 ToolMessage 添加回去
		replaced.append(message)
		# 修复的附件添加到 pending 由上面的 not is_target_message 分支消费
		pending.append(HumanMessage(tool_output, id=f"image-{tc_id}"))
		
		# 改变 is_changed 标志位
		if not is_changed:
			is_changed = True
	
	# 兜底
	# 最后一条信息是 ToolMessage 的话 pending 会残留元素
	if pending:
		replaced.extend(pending)
	
	return {"messages": Overwrite(replaced)} if is_changed else None
