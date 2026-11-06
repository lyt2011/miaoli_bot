from ...utils		import inject_workspace
from ...protocols	import PluginProtocol
from .models		import PluginMetadata, Dependence
from ...errors		import EntryClassNotFound, MetadataMissingError, NotAPackageError

from pathlib	import Path
from typing		import Any, Dict, List, Self, Union

import sys
import yaml
import tomllib
import importlib.util


class Plugin:
	
	def __init__(self, path: Path, metadata: PluginMetadata) -> None:
		
		self.path		= path
		self.metadata	= metadata
		
		self._instance	: Union[PluginProtocol, None]	= None
		self._config	: Union[Dict[str, Any], None]	= None
	
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
	
	@property
	def dependences(self) -> List[Dependence]:
		return list(self.metadata.dependences)
	
	def is_package(self) -> bool:
		return Path(self.path / "__init__.py").is_file()
	
	async def load(self) -> None:
		
		"""Plugin 实例生命周期 加载"""
		
		if not self.is_package():
			raise NotAPackageError(f"{self.path} 缺失 __init__.py")
		
		self._prepare_config()
		self._build_package()
		self._instantiate_plugin()
		self._inject_data()
		
		await self._instance.on_load()
	
	async def unload(self) -> None:
		
		"""Plugin 实例生命周期 卸载"""
		
		# 卸载包
		for module_name in list(sys.modules):
			if module_name.startswith(f"{self.package_name}.") or module_name == self.package_name:
				del sys.modules[module_name]
		
		# 加载的时候挂了可能还没有赋值
		if self._instance is not None:
			await self._instance.on_close()
		
		self._instance = None
	
	def _prepare_config(self) -> None:
		
		"""准备插件的 config；没有则跳过"""
		
		# 没有则不加载 config
		cfg_file = Path(self.path / "config.yaml")
		if not cfg_file.is_file():
			return None
		
		# 加载并给 "$workspace" 占位符注入路径
		config = yaml.safe_load(cfg_file.read_bytes())
		config = inject_workspace(config, str(self.path))
		
		self._config = config
	
	def _build_package(self) -> None:
		
		"""
		不能把这四个步骤分开
		
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
		module = importlib.util.module_from_spec(specification)
		
		# 注册包 self.package_name 作为包名
		sys.modules[self.package_name] = module
		
		# 执行 module 的代码
		specification.loader.exec_module(module)
	
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
