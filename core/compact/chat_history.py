from langchain_core.messages	import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from .utils	import extract_content, extract_tool_calls

from typing	import List, Self


class ChatHistory:
	
	"""纯容器聊天历史 不处理具体业务逻辑"""

	def __init__(self) -> None:
		self.history: List[str]	= []
	
	@classmethod
	def from_messages(cls, messages: List[BaseMessage]) -> Self:
		
		instance = cls()
		
		for message in messages:
		
			# 所有的 message 都直接添加正文提取内容
			instance.add_any(message, extract_content(message))
			
			# 对于带有 tool_calls 的 AIMessage 需要单独加记录
			if isinstance(message, AIMessage) and message.tool_calls:
				for tc_content in extract_tool_calls(message):
					instance.add_tool_call(tc_content)
		
		return instance
	
	def to_history(self) -> List[str]:
		return list(self.history)
	
	def add_assistant(self, content: str) -> None:
		self.history.append(f"[Assistant]: {content}")
	
	def add_user(self, content: str) -> None:
		self.history.append(f"[User]: {content}")
	
	def add_tool_call(self, content: str) -> None:
		self.history.append(f"[Assistant tool call]: {content}")
	
	def add_tool_result(self, content: str) -> None:
		self.history.append(f"[ToolResult]: {content}")
	
	def add_any(self, message: BaseMessage, content: str) -> None:
		
		"""添加任意类型的消息 注意不会处理 AIMessage.tool_calls"""
		
		if isinstance(message, AIMessage):
			self.add_assistant(content)
	
		elif isinstance(message, HumanMessage):
			self.add_user(content)
		
		elif isinstance(message, ToolMessage):
			self.add_tool_result(content)
		
		elif isinstance(message, SystemMessage):
			pass # 对于系统提示词直接丢掉 不该压缩系统提示词
		
		else: # 对于不认识的类型直接加一条 Unknown 信息
			self.history.append(f"[Unknown]: {content}")
		
		return None
