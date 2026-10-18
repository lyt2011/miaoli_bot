from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE


def get_admin_id() -> str:
	"""获取管理员id 返回字符串"""
	return str(SHARE_STORE.recall(PLUGIN_CONFIG).account.admin_id)

def get_bot_id() -> str:
	"""获取机器人id 返回字符串"""
	return str(SHARE_STORE.recall(PLUGIN_CONFIG).account.bot_id)

def get_admin_nickname() -> str:
	"""获取管理员昵称 返回字符串"""
	return str(SHARE_STORE.recall(PLUGIN_CONFIG).account.admin_nickname)

def get_bot_nickname() -> str:
	"""获取机器人昵称 返回字符串"""
	return str(SHARE_STORE.recall(PLUGIN_CONFIG).account.bot_nickname)
