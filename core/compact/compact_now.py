from langchain_core.language_models	import BaseChatModel
from langchain_core.messages		import BaseMessage, SystemMessage

from .chat_history	import ChatHistory
from .utils			import prune_messages, truncate_content_if_need
from .consts		import COMPACT_PROMPT, SUMMARY_TAG
from .runtimes		import CompactFailed, CompactSuccess

from datetime	import datetime
from typing		import List, Union


async def compact_now(
	messages		: List[BaseMessage],
	client			: BaseChatModel,
	retain_tokens	: int,
	*,
	max_characters	: int	= 2000,
) -> Union[CompactSuccess, CompactFailed]:
	
	"""立即压缩 messages 无论是否该压缩"""
	
	if not messages:
		return CompactFailed(reason="没有可压缩内容")
	
	# 计算开始时间 便于优化性能
	s_time = datetime.now()
	
	# 对 messages 进行剪枝
	tokens_bef, tokens_aft, messages_aft = prune_messages(messages, retain_tokens)
	
	# 用原 messages 生成对话历史记录 并按 max_characters 对其进行截断
	history	= ChatHistory.from_messages(messages).to_history()
	history	= "\n\n".join([truncate_content_if_need(ctx, max_characters) for ctx in history])
	
	# 基于 COMPACT_PROMPT 构建请求 对 history 进行真实压缩
	ai_message	= await client.ainvoke([SystemMessage(COMPACT_PROMPT), history])
	summary		= ai_message.content.strip()
	
	# 对于空摘要 直接返回 CompactFailed
	if not summary:
		return CompactFailed(reason="模型返回了空摘要")
	
	# 太长了单独构建 CompactSuccess
	result =  CompactSuccess(
		summary			= f"<{SUMMARY_TAG}>\n{summary}\n</{SUMMARY_TAG}>",
		used_time		= (datetime.now() - s_time).total_seconds(),	
		tokens_before	= tokens_bef,
		tokens_after	= tokens_aft,
		messages_before	= messages,
		messages_after	= messages_aft, # 不帮拼 只输出剪枝后的消息 具体摘要拼法需要自己解决
	)
	
	return result
