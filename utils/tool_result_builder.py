from typing	import Dict, Any


def custom(status: bool, **kwargs) -> Dict[str, Any]:
	return {"status": status, **kwargs}

def fail(message: Any) -> Dict[str, Any]:
	return custom(status=False, message=message)

def success(message: Any) -> Dict[str, Any]:
	return custom(status=True, message=message)