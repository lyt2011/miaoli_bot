from string	import Template
from typing	import Union


def inject_workspace(data: Union[str, list, dict], workspace: str) -> Union[str, list, dict]:
	
	"""为 str/list/dict 注入工作目录 用来给 config 字典用的"""
	
	if isinstance(data, str):
		return Template(data).safe_substitute(workspace=workspace)
	
	if isinstance(data, list):
		return [inject_workspace(d, workspace) for d in data]
	
	if isinstance(data, dict):
		return {k: inject_workspace(v, workspace) for k, v in data.items()}
	
	# 默认原样返回
	return data
