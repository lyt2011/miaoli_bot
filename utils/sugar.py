from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX


def concatenate_id(session_id: str, is_group: bool) -> str:
	"""根据id来源拼接为 来源前缀+id"""
	return f"{GROUP_PREFIX if is_group else PRIVATE_PREFIX}{session_id}"
