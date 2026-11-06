def to_xml_prompt(key: str, value: str) -> str:
	"""将键与值拼接成 xml 结构化字符串"""
	return f"<{key}>\n{value}\n</{key}>"
