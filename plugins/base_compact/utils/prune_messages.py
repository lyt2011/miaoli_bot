from langchain_core.messages	import AIMessage, BaseMessage, SystemMessage, ToolMessage

from .estimate_message_tokens	import estimate_message_tokens

from typing	import List, Tuple


def prune_messages(messages: List[BaseMessage], retain_tokens: int) -> Tuple[float, float, List[BaseMessage]]:
	
	"""
	按 token 预算从最旧的一端剪枝 直到上下文 tokens 少于 retain_tokens
	SystemMessage / ToolMessage / 带 tool_calls 的 AIMessage 一律不剪
	返回剪枝前 tokens / 剪枝后 tokens / 剪枝后的消息列表副本 不改动入参
	"""
	
	# 转为不变索引
	ctxs = {index: messages[index] for index in range(len(messages))}
	
	# 实际减的那个和副本 用于区分剪枝前后的 tokens 避免再算一次
	tokens_noumenon	= sum(estimate_message_tokens(message) for message in messages)
	tokens_snapshot = tokens_noumenon
	
	for index, message in tuple(ctxs.items()):
		
		# 对于剩余 tokens 小于等于 保留 tokens 时直接返回
		if tokens_snapshot <= retain_tokens:
			break
		
		# 对于 SystemMessage/ToolMessage 则跳过
		if isinstance(message, (SystemMessage, ToolMessage)):
			continue
		
		# 带 tool_calls / invalid_tool_calls 的也跳过	
		if isinstance(message, AIMessage) and (message.tool_calls or message.invalid_tool_calls):
			continue
		
		# 从上下文列表移除 message
		del ctxs[index]
		
		# 减去该消息的 token
		tokens_snapshot -= estimate_message_tokens(message)
	
	return tokens_noumenon, tokens_snapshot, list(ctxs.values())
