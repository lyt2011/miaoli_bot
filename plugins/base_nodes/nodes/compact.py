from langchain_core.messages	import HumanMessage

from langgraph.runtime	import Runtime
from langgraph.types	import Overwrite
from langgraph.config	import get_config

from miaoli_bot.api		import get_model_info
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_bot.core	import CompactFailed, compact_now, estimate_message_tokens

from ..utils	import get_compaction_range

from typing	import Dict, Any, Optional

import logging


LOGGER = logging.getLogger("CompactIfNeed")


async def compact_if_need(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	client		= runtime.context["client"]
	messages	= state["messages"]
	tid			= get_config()["configurable"]["thread_id"]
	config		= get_model_info()
	
	# 对当前上下文立即求 tokens 数量 对于当前 token 小于 (上下文 - 最大输出) 保留值则不压缩
	tokens = sum(estimate_message_tokens(message) for message in messages)
	if tokens < (config["context_window"] - config["max_tokens"]):
		return None

	compaction_range = get_compaction_range(messages)
	if compaction_range is None:
		return None
	p_start, p_end = compaction_range

	# NOTE: 默认值最大字符 我也不知道配置写哪里好了
	# HACK: 硬编码保留 token 这个我也不知道把配置写哪好了
	result = await compact_now(messages[p_start: p_end + 1], client, 20000)
	
	if isinstance(result, CompactFailed):
		LOGGER.error(f"因为 {result.reason} 压缩失败了", exc_info=result.exception)
	
	else:
		
		LOGGER.info(f"thread_id: {tid} 上下文压缩完成 "
			f"压缩前 tokens: {result.tokens_before}, 压缩后 tokens: {result.tokens_after} "
			f"压缩前消息数量 {len(result.messages_before)}, 压缩后消息数量: {len(result.messages_after)} "
			f"收敛: {result.tokens_after < result.tokens_before}")
		
		# 搞半天还要自己拼
		compacted_ctx = [
			*messages[:p_start], # 得开始点前面的上下文 如系统提示词
			HumanMessage(result.summary), # summary 是带有标签的摘要
			*result.messages_after, # 把压缩器剪枝后的 messages 塞回去
			*messages[p_end + 1:] # 把结束点之后的上下文塞回去 如 带tc的AIMessage/ToolMessage
		]
		
		return {"messages": Overwrite(compacted_ctx)}
	
	return None