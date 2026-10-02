from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any, Optional, List

from langgraph.runtime			import Runtime
from langchain_core.messages	import (
	AIMessage,
	HumanMessage,
	SystemMessage,
	ToolMessage,
	RemoveMessage,
)
from langgraph.graph.message	import REMOVE_ALL_MESSAGES


# HACK: 测试期用常量 懒得从配置拿
MAX_KEEP_MESSAGES	= 5
CONTEXT_WINDOW		= 128000
COMPACT_MESSAGE		= (
	"The context is about to overflow. "
	"Please use the third person to generate a summary for the context."
)


def _last_common_idx(messages: List[Any]) -> int:
	
	"""
	计算「需要保留的起始索引」（返回值永远是一个可切片的索引）
	
	规则：
		从尾部往前数，最多保留 MAX_KEEP_MESSAGES 条 Human/AI 消息
		ToolMessage 随其所属轮次一起保留，但本身不占用配额
		碰到 SystemMessage 停止
		保留区不能以 ToolMessage 开头（否则会切掉发起工具调用的 AIMessage）
	"""
	
	total	= len(messages)
	start	= total
	count	= 0
	
	for idx in range(total - 1, -1, -1):
		
		message = messages[idx]
		
		if isinstance(message, SystemMessage):
			break
		
		if isinstance(message, (AIMessage, HumanMessage)):
			if count >= MAX_KEEP_MESSAGES:
				break
			count += 1
		
		start = idx
	
	# 修配对：保留区以 ToolMessage 开头时，把它发起的 AIMessage 一并纳入
	while start < total:
		
		if not isinstance(messages[start], ToolMessage):
			break
		
		tool_call_id = messages[start].tool_call_id
		origin_idx	 = None
		
		for idx in range(start - 1, -1, -1):
			
			candidate = messages[idx]
			
			if isinstance(candidate, AIMessage) and any(
				tool_call.get("id") == tool_call_id
				for tool_call in (candidate.tool_calls or [])
			):
				origin_idx = idx
				break
		
		if origin_idx is None:
			start += 1			# 找不到发起的 AIMessage 只能丢掉这条孤儿
			continue
		
		start = origin_idx
	
	return start


async def compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""上下文超限时 把历史压成一条摘要"""
	
	messages	= state.get("messages", [])
	
	# HACK: 大致算一下
	tokens		= sum(len(ctx.content or "") for ctx in messages)
	
	if CONTEXT_WINDOW > tokens:
		return None
	
	client		= runtime.context["client"]
	keep_index	= _last_common_idx(messages)
	
	# 摘要请求：system + 历史 + 压缩指令
	prompt		= [SystemMessage(state["system_prompt"]), *messages, HumanMessage(COMPACT_MESSAGE)]
	ai_message	= await client.ainvoke(prompt)
	
	compaction	= f"<compaction>{ai_message.content}</compaction>"
	
	# 整体替换：清空历史，放入摘要 + 保留窗口
	final_messages = [
		RemoveMessage(id=REMOVE_ALL_MESSAGES),
		HumanMessage(compaction),
		*messages[keep_index:],
	]
	
	return {"messages": final_messages}
