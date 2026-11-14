from ..consts	import DEFAULT_TEXT_RATIO


def estimate_text_tokens(text: str) -> float:
	"""按字符数粗估一段纯文本的 token 数"""
	return len(text) * DEFAULT_TEXT_RATIO
