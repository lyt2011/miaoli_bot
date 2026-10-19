from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing						import Any, Dict
from langgraph.runtime			import Runtime
from langgraph.types			import Overwrite
from langchain_core.messages	import HumanMessage

from ..consts	import PLUGIN_CONFIG
from ..utils	import keep_recent_messages


async def compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""上下文压缩节点 —— 由 should_compact 判定需要压缩后才进来"""
	
	plugin_cfg	= store_recall(PLUGIN_CONFIG)
	
	messages = state.get("messages", [])
	if not messages:
		return Abort(reason="完全无内容可被压缩")
	
	# 构建压缩请求上下文
	compact_ctx	= [*messages, HumanMessage(plugin_cfg.prompt)]
	
	# 通过大模型压缩上下文
	# 保留有效信息
	# 生成 HumanMessage 摘要
	ai_message	= await runtime.context["client"].ainvoke(compact_ctx)
	kp_messages	= keep_recent_messages(messages, n=plugin_cfg.keep_count)
	compaction	= HumanMessage(f"<compaction>{ai_message.content}</compaction>")
	
	# 生成压缩后的上下文并回填系统提示词
	compacted_ctx = [compaction, *kp_messages]
	if isinstance(message[0], SystemMessage):
		compacted_ctx.insert(0, message[0])
	
	# 覆盖messages
	return {"messages": Overwrite(compacted_ctx)}
