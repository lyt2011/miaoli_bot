from typing					import Any, Dict, List, Union

from ..consts				import DEFAULT_PAYLOAD_TOKENS
from .estimate_text_tokens	import estimate_text_tokens


def estimate_content_tokens(content: Union[str, list]) -> float:
	
	"""
	估算 content 的 token 会计算多模态内容
	返回未取整的 float 取整与舍入由调用方决定
	"""
	
	if isinstance(content, str):
		return estimate_text_tokens(content)
	
	return _estimate_blocks(content)


def _estimate_blocks(blocks: List[Union[str, Dict[str, Any]]]) -> float:
	
	total = 0.0
	
	for block in blocks:
		
		# 对于字符串块 (openai 官方不支持 但是库支持)
		if isinstance(block, str):
			total = total + estimate_text_tokens(block)
		
		elif isinstance(block, dict):
			
			text = block.get("text")
			if text is not None:
				total = total + estimate_text_tokens(text)
			
			elif block.get("image_url"):
				# 一张图按常量兜底 不解析 base64 载荷
				total = total + DEFAULT_PAYLOAD_TOKENS
			
			else:
				total = total + DEFAULT_PAYLOAD_TOKENS
		else:
			raise TypeError(f"未知的多模态数组类型: {type(block).__name__}")
	
	return total
