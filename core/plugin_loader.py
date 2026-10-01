import importlib
import importlib.util
import sys
import tomllib
import yaml

from pathlib	import Path
from typing		import Any, Dict, List, Self

from pydantic	import BaseModel, Field, FilePath

from ..models		import PluginConfig
from ..protocols	import PluginProtocol
from .registry		import Registry


CONFIG_NAME		= "plugin.toml"
PACKAGE_PREFIX	= "miaoli_bot_subplugin"

SubPlugins = Dict[str, PluginProtocol]


class SubPluginConfig(BaseModel):
	
	enter_class	: str		= Field(..., description="入口类")
	enter_file	: FilePath	= Field(..., description="入口文件")
	
	@classmethod
	def from_toml(cls, path: Path) -> Self:
		
		folder		= Path(path).parent
		toml_data	= tomllib.loads(Path(path).read_text(encoding="utf-8"))
		
		toml_data["enter_file"] = str(folder / toml_data["enter_file"])
		
		return cls.model_validate(toml_data)


class PluginLoader:
	
	def __init__(self, path: Path, config: PluginConfig, registry: Registry) -> None:
		
		self.path		: Path			= Path(path)
		self.config		: PluginConfig	= config
		self.registry	: Registry		= registry
		self.plugins	: SubPlugins	= {}
	
	def discover(self) -> List[Path]:
		
		"""扫出所有「带 plugin.toml 的直接子目录」"""
		
		return sorted(p for p in self.path.iterdir() if (p / CONFIG_NAME).is_file())
	
	def _register_package(self, folder: Path) -> str:
		
		"""把文件夹注册成 Python 的「包」，返回包名
		
		就是手动做掉 import 语句背后的 3 步，缺一不可：
			① 造 spec —— submodule_search_locations 决定它是不是「包」（有没有 __path__），
			   入口文件里的 `from .helper import x` 就靠它找；location 必须是文件，
			   实测传目录本身会返回 None
			② 造空壳 —— 只造模块对象，不执行文件里的代码
			③ 登记 + 执行 —— 登记必须放在 exec 之前，
			   否则文件里的相对 import 找不到父包（attempted relative import with no known parent package）
		"""
		
		pkg = f"{PACKAGE_PREFIX}_{folder.name}"
		
		if pkg in sys.modules:				# 加载过就复用，不要重新 exec
			return pkg
		
		spec	= importlib.util.spec_from_file_location(
			pkg,
			folder / "__init__.py",
			submodule_search_locations=[str(folder)],
		)
		module	= importlib.util.module_from_spec(spec)
		
		sys.modules[pkg] = module
		spec.loader.exec_module(module)
		
		return pkg
	
	@staticmethod
	def _load_plugin_config(folder: Path) -> Dict[str, Any]:
		
		config_path = folder / "config.yaml"
		if not config_path.is_file():
			return {}
		
		config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
		if config is None:
			return {}
		if not isinstance(config, dict):
			raise TypeError(f"子插件配置必须是字典: {config_path}")
		
		return config

	async def load(self, folder: Path) -> PluginProtocol:
		
		"""加载一个子插件目录：读 toml/config → 注册成包 → import 入口 → on_load"""
		
		cfg		= SubPluginConfig.from_toml(folder / CONFIG_NAME)
		pkg		= self._register_package(folder)
		entry	= importlib.import_module(f"{pkg}.{cfg.enter_file.stem}")
		
		plugin	= getattr(entry, cfg.enter_class)(
			config		= self._load_plugin_config(folder),
			registry	= self.registry,
		)
		
		await plugin.on_load()
		self.plugins[folder.name] = plugin
		
		return plugin
	
	async def load_all(self) -> None:
		
		for folder in self.discover():
			await self.load(folder)
	
	async def unload(self, name: str) -> None:
		
		"""卸载：on_close + 把整包从 sys.modules 抹掉
	
		不抹的话，下次加载会直接从缓存里拿到**旧的模块对象**，改了代码也不生效。
		"""
		
		await self.plugins.pop(name).on_close()
		
		pkg = f"{PACKAGE_PREFIX}_{name}"
		
		for key in [k for k in sys.modules if k == pkg or k.startswith(f"{pkg}.")]:
			del sys.modules[key]
	
	async def unload_all(self) -> None:
		
		for name in list(self.plugins):
			await self.unload(name)
