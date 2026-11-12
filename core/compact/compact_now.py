from langchain_core.language_models	import BaseChatModel
from langchain_core.messages		import BaseMessage, SystemMessage

from .chat_history	import ChatHistory
from .token_pruner	import TokenPruner
from .utils			import truncate_content_if_need
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
	
	"""立即压缩 messages"""
	
	if not messages:
		return CompactFailed(reason="没有可压缩内容")
	
	# 计算开始时间 便于优化性能
	s_time = datetime.now()
	
	# 生成对话历史记录 并按 max_characters 对其进行截断
	history	= ChatHistory.from_messages(messages).to_history()
	history	= "\n\n".join([truncate_content_if_need(ctx, max_characters) for ctx in history])
	
	# 基于 COMPACT_PROMPT 构建请求 进行真实压缩
	ai_message	= await client.ainvoke([SystemMessage(COMPACT_PROMPT), history])
	summary		= ai_message.content.strip()
	
	# 对于空摘要 直接返回 CompactFailed
	if not summary:
		return CompactFailed(reason="模型返回了空摘要")
	
	# 获取剪枝前的 tokens
	decreaser	= TokenPruner.from_messages(messages)
	tokens_bef	= decreaser.get_remaining_tokens()
	
	# 对会话进行剪枝
	decreaser.prune(retain_tokens=retain_tokens)
	
	# 获取压缩后的 token 与上下文
	tokens_aft	= decreaser.get_remaining_tokens()
	message_aft	= decreaser.messages
	
	# 太长了单独构建 CompactSuccess
	result =  CompactSuccess(
		summary		= f"<{SUMMARY_TAG}>\n{summary}\n</{SUMMARY_TAG}>",
		used_time	= (datetime.now() - s_time).total_seconds(),
		
		tokens_before	= tokens_bef,
		tokens_after	= tokens_aft,
		
		messages_before	= messages,
		messages_after	= message_aft, # 不帮拼 太jb麻烦了 自己拼
	)
	
	return result
