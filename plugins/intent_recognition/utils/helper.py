from typing	import Any, Dict, List, Optional

from langchain_core.messages	import BaseMessage, HumanMessage


def build_prompt(dt: Dict[str, str], cr: str = "\n") -> str:	
	"""把字典拼成提示词 写 helper 不是为了解耦 是写在 node 里太长了拆出来的"""
	return cr.join([f"<{o_o}>{T_T}</{o_o}>" for o_o, T_T in dt.items()])


def get_content(ctx: Any, cr: str = "\n") -> Optional[str]:
	
	"""适配多模态消息的正文提取"""
	
	if not (content := getattr(ctx, "content", None)):
		return None
	
	# 对于多模态内容的处理 尝试提取 text 并合并
	if isinstance(content, list):
		
		blocks: List[str] = []
		
		for b in content:
			
			match b:
				
				# 只解包字典和匹配字符串 其他不管
				case {"text": str(b_text)}: blocks.append(b_text)
				case str(): blocks.append(b)
				case _: ...
			
		text = cr.join(blocks)
	
	else: text = str(content)
	
	return text

def get_latest_human(messages: List[BaseMessage]) -> Optional[HumanMessage]:
	
	"""匹配最后一条用户信息 可能返回 None"""
	
	for ctx in messages[::-1]:
		if isinstance(ctx, HumanMessage):
			return ctx
	
	return None
