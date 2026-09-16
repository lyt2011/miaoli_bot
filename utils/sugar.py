from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX


def concatenate_id(
	session_id	: str,
	is_group	: bool = False,
) -> str:
	
	prefix = GROUP_PREFIX if is_group else PRIVATE_PREFIX
	
	return f"{prefix}{session_id}"