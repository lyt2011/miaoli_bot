from .base_plugin_error	import BasePluginError


class NotAPackageError(BasePluginError):
	
	"""插件目录缺少 __init__.py"""
	...
