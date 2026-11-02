from langchain_core.messages	import HumanMessage, SystemMessage

from langgraph.runtime	import Runtime
from langgraph.types	import Overwrite

from miaoli_pipeline.actions	import Abort

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import ABSTRACT_TAG, PLUGIN_CONFIG
from ..utils	import keep_recent_messages, read_compact_prompt

from typing	import Any, Dict


async def compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""上下文压缩节点 —— 由 should_compact 判定需要压缩后才进来"""
	
	config	= store_recall(PLUGIN_CONFIG)
	
	if not (messages := state.get("messages", [])):
		return Abort(reason="完全无内容可被压缩")
	
	# 构建压缩请求上下文
	compact_ctx	= [*messages, HumanMessage(read_compact_prompt())]
	# 通过大模型压缩上下文
	ai_message		= await runtime.context["client"].ainvoke(compact_ctx)
	# 保留有效信息
	kept_messages	= keep_recent_messages(messages, n=config.compact.keep_count)
	# 生成 HumanMessage 摘要
	abstract		= HumanMessage(f"<{ABSTRACT_TAG}>{ai_message.content}</{ABSTRACT_TAG}>")
	# 重新构建上下文 把压缩内容放在最前面
	compacted_ctx	= [abstract, *kept_messages]
	
	# 过滤系统提示词 防止压缩之后提示词顺序错乱
	# 并根据实际需求回填系统提示词
	compacted_ctx = [ctx for ctx in compacted_ctx if not isinstance(ctx, SystemMessage)]
	if isinstance(messages[0], SystemMessage) and config.compact.recall_system_prompt:
		compacted_ctx.insert(0, messages[0])
	
	# 覆盖messages
	return {"messages": Overwrite(compacted_ctx)}
