from tiktoken	import Encoding
from typing		import List, Any

from .sugar		import merge_contents


def tiktoken_calculate(messages: List[Any], *, encoding: Encoding) -> int:
	
	"""
	通过 titoken 计算
	自动忽略所有特殊字符
	"""
	
	contents	= merge_contents(messages)
	token_array	= encoding.encode(contents, disallowed_special=())
	return len(token_array)

def base_calculate(messages: List[Any]) -> int:
	
	"""基于 python 线性公式计算"""
	
	contents	= merge_contents(messages)
	tokens		= len(contents) * 0.7
	
	return int(tokens)
