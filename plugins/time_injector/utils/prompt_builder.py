from string		import Template
from datetime	import datetime


def build_time_prompt(template: str, now: datetime) -> str:
	
	"""构建当前时间提示词"""
	
	aware	= now.astimezone()
	strtime	= aware.strftime("%Y-%m-%d %H:%M %z") # 精度越高时间隔越大会导致模型回答越不准确
	weekday	= aware.weekday()
	
	return Template(template).substitute(now=strtime, weekday=weekday+1) # 注意要+1不然星期一拿到的是 weekday=0
