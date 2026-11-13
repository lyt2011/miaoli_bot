from langchain_core.messages	import AIMessage, BaseMessage, SystemMessage, ToolMessage

from .utils	import estimate_message_tokens

from typing	import List, Self


class TokenPruner:
	
	def __init__(self, messages: List[BaseMessage], tokens: List[int]) -> None:
		
		if len(messages) < len(tokens):
			raise ValueError(f"无法对齐 messages 与 tokens")
		
		self.info = list(zip(messages, tokens))
		
	@classmethod
	def from_messages(cls, messages: List[BaseMessage]) -> Self:
		"""从消息数组直接构建实例 内部自动基于公式计算 token"""
		return cls(messages=messages, tokens=[estimate_message_tokens(message) for message in messages])
	
	@property
	def messages(self) -> List[BaseMessage]:
		return [message for message, _ in self.info]
	
	@property
	def remaining_tokens(self) -> int:
		"""这玩意有副作用 纯语法糖 不建议外部使用"""
		return sum(token for _, token in self.info)
	
	def get_remaining_tokens(self) -> int:
		return self.remaining_tokens
	
	def prune(self, retain_tokens: int) -> None:
		
		"""对上下文进行剪枝 存为内部数据 幂等"""
		
		for mt in list(self.info):
			
			# 对于剩余 tokens 小于等于 保留 tokens 时直接返回
			if self.remaining_tokens <= retain_tokens:
				return None
			
			# 对于 SystemMessage/ToolMessage 则跳过
			if isinstance(mt[0], (SystemMessage, ToolMessage)):
				continue
			
			# 带 tool_calls 的也跳过
			if isinstance(mt[0], AIMessage) and mt[0].tool_calls:
				continue
			
			self.info.remove(mt)
		
		return None
