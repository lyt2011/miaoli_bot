from ..models	import Allowed


def is_allowed(thread_id: str, allowed: Allowed) -> bool:
	
	if allowed == "all":
		return True
	
	if allowed and thread_id in allowed:
		return True
	
	return False
