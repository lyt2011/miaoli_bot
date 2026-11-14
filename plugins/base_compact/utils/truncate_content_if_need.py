from ..consts	import TRUNCATED_LABEL, TRUNCATED_TEMPLATE


def truncate_content_if_need(content: str, max_characters: int) -> str:
	
	"""截断多余的字符并打上 TRUNCATED_LABEL 标签"""
	
	# 对于小于 max_characters 的内容不能乱插标签
	content_length = len(content)
	if content_length <= max_characters:
		return content
	
	# 先计算截断后面的字符是多少个
	truncated_characters = content_length - max_characters
	if truncated_characters <= len(TRUNCATED_LABEL):
		return content # 对于截完之后还变长/不变的压根不需要截
	
	# 截断并打标签
	return content[:max_characters] + TRUNCATED_TEMPLATE.substitute(n=truncated_characters)
