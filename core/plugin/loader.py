from .plugin			import Plugin
from .plugin_entity		import PluginEntity
from .utils				import topology_sort_plugins

from contextlib	import suppress
from pathlib	import Path
from typing		import Dict, List

import logging


LOGGER = logging.getLogger("Loader")


class Loader:
	
	def __init__(self, paths: List[Path]) -> None:
		
		self.paths		= paths
		self.entities	: List[PluginEntity] = []
	
	@property
	def entity_mapping(self) -> Dict[str, PluginEntity]:
		"""插件名 到 登记行的映射"""
		return {entity.plugin.package_name: entity for entity in self.entities}
	
	@property
	def status(self) -> Dict[str, List[Plugin]]:
		
		"""按状态分出各批插件"""
		
		status = {
			"prepared": [entity.plugin for entity in self.entities if entity.is_prepared()],
			"loaded": [entity.plugin for entity in self.entities if entity.is_loaded()],
			"unloaded": [entity.plugin for entity in self.entities if entity.is_unloaded()],
			"erred": [entity.plugin for entity in self.entities if entity.is_erred()],
		}
		
		return status
	
	def prepare_plugins(self) -> None:
		
		"""收集插件并转 PluginEntity"""
		
		# 先不做去重
		# package_names	= [p.package_name for p in plugins]
		# repeated_names	= [name for name, count in Counter(package_names).items() if count > 1]
		# if repeated_names:
		
		self.entities = [
			PluginEntity(plugin=plugin)
			for plugin in self._collect_plugins()
		]
		
		LOGGER.info(f"共收集 {len(self.entities)} 个插件: "
			f"{[entity.plugin.package_name for entity in self.entities]}")
	
	async def load_plugins(self) -> None:
		
		"""拓扑序加载插件 (含激活)"""
		
		for plugin in topology_sort_plugins(self.status["prepared"]):
			
			# 依赖没加载成功的 直接跳过
			if missing := self._missing_dependences(plugin):
				
				LOGGER.warning(f"插件 {plugin.package_name} 跳过: "
					f"依赖 {missing} 加载失败")
				
				continue
			
			try:
				await plugin.load()
			
			except Exception as exception:
				
				# 安全回滚
				with suppress(Exception):
					await plugin.unload()
				
				LOGGER.error(f"插件 {plugin.package_name} 加载失败: "
					f"{type(exception).__name__}: {exception}", exc_info=exception)
				
				self.entity_mapping[plugin.package_name].mark_erred(exception)
			
			else:
				self.entity_mapping[plugin.package_name].mark_loaded()
		
		LOGGER.info(f"成功加载: {len(self.status['loaded'])}/{len(self.entities)}")
	
	async def unload_plugins(self) -> None:
		
		"""倒拓扑序卸载插件"""
		
		for plugin in topology_sort_plugins(self.status["loaded"])[::-1]:
			
			try:
				await plugin.unload()
			
			except Exception as exception:
				
				LOGGER.error(f"插件 {plugin.package_name} 卸载失败: "
					f"{type(exception).__name__}: {exception}", exc_info=exception)
				
				self.entity_mapping[plugin.package_name].mark_erred(exception)
			
			else:
				self.entity_mapping[plugin.package_name].mark_unloaded()
		
		LOGGER.info(f"成功卸载: {len(self.status['unloaded'])}/{len(self.entities)}")
	
	def _missing_dependences(self, plugin: Plugin) -> List[str]:
		
		"""返回加载失败的依赖名 未被收集到的依赖不算"""
		
		return [
			dependence.name for dependence in plugin.metadata.dependences
			if (entity := self.entity_mapping.get(dependence.name)) and entity.is_erred()
		]
	
	def _collect_plugins(self) -> List[Plugin]:
		
		"""
		收集子插件并实例化为 Plugin 对象
		一个插件缺少元信息会全炸
		"""
		
		# 展开路径并过滤非文件夹路径
		expanded_paths	= [p_path for path in self.paths for p_path in path.iterdir()]
		expanded_paths	= [p_path for p_path in expanded_paths if p_path.is_dir()]
		
		# 收集子插件并过滤非包 Plugin 对象
		plugins	= [Plugin.from_path(path) for path in expanded_paths]
		plugins	= [plugin for plugin in plugins if plugin.is_package()] # 过滤非包插件实例
		
		return plugins
