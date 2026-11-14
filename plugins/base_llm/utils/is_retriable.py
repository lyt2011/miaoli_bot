def is_retriable(exc: Exception) -> bool:
	
	"""判断异常是否可重试 暂时一律不做重试"""
	
	return False
