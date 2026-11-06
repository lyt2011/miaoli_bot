from langchain_core.messages	import BaseMessage

from typing					import Dict, Union


def build_prompt(dt: Dict[str, str], cr: str = "\n") -> str:	
	"""把字典拼成提示词 写 helper 不是为了解耦 是写在 node 里太长了拆出来的"""
	return cr.join([f"<{o_o}>{T_T}</{o_o}>" for o_o, T_T in dt.items()])

def content_to_text(ctx: BaseMessage) -> str:
	
	"""适配多模态消息的正文提取"""
	
	content = ctx.content
	
	if isinstance(content, str):
		return content
	
	if isinstance(content, list):
		return "\n".join([block_to_text(b) for b in content])
	
	# 兜底返回空文本
	return ""

def block_to_text(block: Union[str, dict]) -> str:
	
	"""多模态块转纯文本"""
	
	if isinstance(block, str):
		return block
	
	if (text := block.get("text")) and isinstance(text, str):
		return text
	
	# 兜底返回空文本	
	return ""
