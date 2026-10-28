from pathlib	import Path
from typing		import Iterable, List

from .plugin	import Plugin

import logging


LOGGER = logging.getLogger("Loader")


class Loader:
	
	def __init__(self, paths: List[Path]) -> None:
		
		self.paths = paths
		
		self._prepared	: set[Plugin]	= set()
		self._erred		: set[Plugin]	= set()
		self._loaded	: List[Plugin]	= [] # loaded 是基于 prepared 计算得出且需要顺序的 只能使用 List
	
	def mark_prepared(self, plugin: Plugin) -> None:
		"""标注插件已准备"""
		self._prepared.add(plugin)
	
	def mark_erred(self, plugin: Plugin) -> None:
		"""标注插件已错误"""
		self._erred.add(plugin)
	
	def mark_loaded(self, plugin: Plugin) -> None:
		"""标注插件已加载"""
		self._loaded.append(plugin)
	
	def is_prepared(self, plugin: Plugin) -> bool:
		"""插件是否已准备"""
		return plugin in self._prepared
	
	def is_loaded(self, plugin: Plugin) -> bool:
		"""插件是否已加载"""
		return plugin in self._loaded
	
	def is_erred(self, plugin: Plugin) -> bool:
		"""插件是否已错误"""
		return plugin in self._erred
	
	def expand_paths(self) -> List[Path]:
		"""展开为单个插件文件夹路径"""
		return [p_path for path in self.paths for p_path in path.iterdir()]
		
	def prepare_plugins(self) -> None:
		
		"""准备插件实例 一个插件缺少元信息会全炸(故意的)"""
		
		plugins = [Plugin.from_path(path) for path in self.expand_paths() if path.is_dir()]
		plugins	= [plugin for plugin in plugins if plugin.is_package()] # 过滤非包插件实例
		
		for plugin in plugins:
			self.mark_prepared(plugin)
	
	async def load_plugins(self) -> None:
		
		"""
		安全地加载所有已准备的插件
		加载或激活失败会立即停下并执行资源清理
		"""
		
		for plugin in tp_sort(self._prepared):
			
			if self.is_loaded(plugin):
				LOGGER.warning(f"{plugin.package_name} 已经被加载 跳过")
				continue
			
			if self.is_erred(plugin):
				LOGGER.warning(f"{plugin.package_name} 曾经存在错误 跳过")
				continue
			
			# 加载插件 失败就安全卸载
			is_load_success = safe_load_plugin(plugin)
			if not is_load_success:
				
				safe_unload_plugin(plugin)
				self.mark_erred(plugin)
				
				continue
			
			# 激活插件 失败就安全停用
			is_activate_success = await safe_activate_plugin(plugin)
			if not is_activate_success:
				
				await safe_deactivate_plugin(plugin)
				self.mark_erred(plugin)
				
				continue
			
			# 加载+激活同时成功才添加到 loaded
			self.mark_loaded(plugin)
	
	async def unload_plugins(self) -> None:
		
		"""卸载所有已准备插件 卸载失败不会移除出 loaded"""
		
		for plugin in self._loaded[::-1]:
			
			# 安全停用插件
			is_deactivate_success = await safe_deactivate_plugin(plugin)
			if not is_deactivate_success:
				self.mark_erred(plugin)
			
			# 安全卸载插件 失败则跳过
			is_unload_success = safe_unload_plugin(plugin)
			if not is_unload_success:
				self.mark_erred(plugin)
			
			self._loaded.remove(plugin)


def tp_sort(plugins: Iterable[Plugin]) -> List[Plugin]:
	"""对插件进行拓扑排序"""
	return list(plugins) # HACK: 懒得写 直接返回

def safe_load_plugin(plugin: Plugin) -> bool:

	"""受保护的插件实例生命周期 加载"""

	try:
		plugin.load()

	except Exception as e:
		LOGGER.error(f"插件实例 {plugin.package_name} 加载失败: {e}")
		return False

	return True

async def safe_activate_plugin(plugin: Plugin) -> bool:

	"""受保护的插件生命周期 激活"""

	try:
		await plugin.activate()

	except Exception as e:
		LOGGER.error(f"插件 {plugin.package_name} 激活失败: {e}")
		return False

	return True

async def safe_deactivate_plugin(plugin: Plugin) -> bool:

	"""受保护的插件生命周期 停用"""

	try:
		await plugin.deactivate()

	except Exception as e:
		LOGGER.error(f"插件 {plugin.package_name} 停用失败: {e}")
		return False

	return True

def safe_unload_plugin(plugin: Plugin) -> bool:

	"""受保护的插件实例生命周期 卸载"""

	try:
		plugin.unload()

	except Exception as e:
		LOGGER.error(f"插件实例 {plugin.package_name} 卸载失败: {e}")
		return False

	return True