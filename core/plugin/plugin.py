from pathlib	import Path
from typing		import Any, Dict, Optional, Self
from types		import ModuleType

from ...protocols	import PluginProtocol

from .errors	import EntryClassNotFound, MetadataMissingError, NotAPackageError
from .models	import PluginMetadata

import importlib.util
import sys
import tomllib
import yaml


class Plugin:
	
	def __init__(self, path: Path, metadata: PluginMetadata) -> None:
		
		self.path		= path
		self.metadata	= metadata
		
		self._instance	: Optional[PluginProtocol]	= None
		self._module	: Optional[ModuleType]		= None
		self._config	: Optional[Dict[str, Any]]	= None
	
	@classmethod
	def from_path(cls, path: Path) -> Self:
		
		"""从任意存在 "metadata.toml" 的文件夹直接实例化 Plugin"""
		
		metadata_file = Path(path / "metadata.toml")
		if not metadata_file.is_file():
			raise MetadataMissingError(f"{metadata_file} 元数据缺失")
		
		metadata = PluginMetadata.model_validate(tomllib.load(metadata_file.open("rb")))
		
		return cls(path=path, metadata=metadata)
	
	@property
	def package_name(self) -> str:
		return self.path.name
	
	def is_package(self) -> bool:
		return Path(self.path / "__init__.py").is_file()
	
	def load(self) -> None:
		
		"""Plugin 实例生命周期 加载"""
		
		if not self.is_package():
			raise NotAPackageError(f"{self.path} 缺失 __init__.py")
		
		self._prepare_config()
		self._build_package()
		self._instantiate_plugin()
		self._inject_data()
	
	async def activate(self) -> None:
		"""插件实例 on_load 方法转发"""
		await self._instance.on_load()
	
	async def deactivate(self) -> None:
		"""插件实例 on_close 方法转发"""
		await self._instance.on_close()
	
	def unload(self) -> None:
		"""Plugin 实例生命周期 卸载"""
		unregister_module(self.package_name)
	
	def _prepare_config(self) -> None:
		
		"""准备插件的 config；没有则跳过"""
		
		# 没有则不加载 config
		cfg_file = Path(self.path / "config.yaml")
		if not cfg_file.is_file():
			return None
		
		self._config = yaml.safe_load(cfg_file.read_bytes())
	
	def _build_package(self) -> None:
		
		"""
		不能把
		  importlib.util.spec_from_file_location
		  importlib.util.module_from_spec
		  register_module
		  specification.loader.exec_module
		分开
		
		如果分开了的话封装的意义就不存在了
		不能为了解耦而乱分函数
		"""
		
		# 造包 specification 实例
		specification = importlib.util.spec_from_file_location(
			self.package_name,
			str(self.path / "__init__.py"),
			submodule_search_locations=[str(self.path)]
		)
		
		# 造 module 实例
		self._module = importlib.util.module_from_spec(specification)
		# 注册包
		register_module(name=self.package_name, module=self._module)
		# 执行 module 的代码
		specification.loader.exec_module(self._module)
	
	def _instantiate_plugin(self) -> None:
		
		"""实例化插件"""
		
		module_paths		= self.metadata.entry_class.split(".")
		full_module_name	= ".".join([self.package_name, *module_paths[:-1]])
		class_name			= module_paths[-1]
		
		module	= importlib.import_module(full_module_name)
		cls		= getattr(module, class_name, None)
	
		if cls is None:
			raise EntryClassNotFound(f"{full_module_name} 中找不到类 {class_name}")
		
		if not issubclass(cls, PluginProtocol):
			raise TypeError(f"{full_module_name} 不是插件类")
		
		self._instance = cls()
	
	def _inject_data(self) -> None:
		
		"""注入数据"""
		
		setattr(self._instance, "workspace", self.path)
		setattr(self._instance, "metadata", self.metadata)
		setattr(self._instance, "config", self._config)


def register_module(name: str, module: ModuleType) -> None:
	"""注册模块"""
	sys.modules[name] = module

def unregister_module(name: str) -> None:
	
	"""批量清理模块 "name."开头与 "name" 本身都会被删"""
	
	for module_name in list(sys.modules.keys()):
		if module_name.startswith(f"{name}.") or module_name == name:
			del sys.modules[module_name]
