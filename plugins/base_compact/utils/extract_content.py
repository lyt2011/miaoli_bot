from langchain_core.messages	import BaseMessage


def extract_content(message: BaseMessage) -> str:
	
	"""仅提取 BaseMessage 的文本内容"""
	
	# 真可能没有吗🤔
	assert hasattr(message, "content")
	assert isinstance(message.content, (list, str))
	
	# 对于纯文本 content 直接用自己
	if isinstance(message.content, str):
		extracted = message.content
	
	# 对于列表 content 只提取纯文本其他内容无用
	if isinstance(message.content, list):
		
		# AI 专门测试过 deepseek api 不支持 List[str]
		# 但库对于 content 的注解是 str | List[dict, str]
		# 为了防止奇怪的输入 需要对额外情况做判断
		extracted = "".join([
			(block.get("text") or "")
			if isinstance(block, dict) else str(block)
			for block in message.content
		])
	
	return extracted
