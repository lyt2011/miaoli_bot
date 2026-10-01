from typing		import Optional, List

from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX


def concatenate_id(session_id: str, is_group: bool) -> str:
	
	prefix = GROUP_PREFIX if is_group else PRIVATE_PREFIX
	
	return f"{prefix}{session_id}"

def split_string(string: str, separator: Optional[str] = None) -> List[str]:
	
	if not separator:
		return [string]
	
	return string.split(separator)