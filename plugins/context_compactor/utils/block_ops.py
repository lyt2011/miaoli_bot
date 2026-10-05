from typing						import Any, Dict, List, Union

from .image_ops					import image_to_tokens


HOLDER = "图"


def handle_block(block: List[Union[str, Dict[str, Any]]]) -> str:
	
	"""处理多模态块"""
	
	total = ""
	
	for content in block:
		
		if isinstance(content, dict):
			total += handle_dict_block(content)
		
		elif isinstance(content, str):
			total += handle_str_block(content)
		
		else: continue
	
	return total

def handle_dict_block(content: Dict[str, Any]) -> str:
	
	"""处理字典多模态"""
	
	total = ""
	
	if "type" not in content:
		return total
	
	if content["type"] == "image_url":
		total += HOLDER * image_to_tokens(content)
	
	elif content["type"] == "text":
		total += str(content.get("text", ""))
	
	else: total += HOLDER * 1000 # TODO: 根据实际需求添加模态计算支持
	
	return total

def handle_str_block(content: str) -> str:
	"""处理字符串多模态"""
	return content
