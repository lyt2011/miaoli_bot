from pydantic	import BaseModel, Field, ConfigDict, model_validator, PrivateAttr
from typing		import Optional, Self, Dict
from pathlib	import Path

from .provider		import Provider
from .account		import Account
from .sub_plugin	import SubPluginConfig
from .check_pointer	import CheckPointerConfig
from .split			import SplitConfig
from .typing		import TypingConfig


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")

	prompt_file: Optional[str]	= Field(default=None, description="系统提示词文件")
	
	provider	: str					= Field(..., description="将要使用的供应商")
	model		: str					= Field(..., description="将要使用的模型")
	providers	: Dict[str, Provider]	= Field(default_factory=dict, description="供应商", min_length=1)
	
	account		: Account				= Field(..., description="账号信息配置")
	checkpointer: CheckPointerConfig	= Field(default_factory=CheckPointerConfig, description="check_pointer 数据库配置")
	sub_plugin	: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	split		: SplitConfig			= Field(default_factory=SplitConfig, description="分割配置")
	typing		: TypingConfig			= Field(default_factory=TypingConfig, description="打字速度配置")
	
	_prompt: str = PrivateAttr(default="")
	
	
	@property
	def prompt(self) -> str:
		
		"""
		懒加载提示词
		空文件会导致每次调用都加载，这是故意的
		"""
		
		if self.prompt_file and not self._prompt:
			self._prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self._prompt
	
	@model_validator(mode="after")
	def ensure_model_available(self) -> Self:
		
		if self.provider not in self.providers or self.model not in self.providers[self.provider].models:
			raise ValueError(F"模型: {self.provider}/{self.model} 未配置")
		
		return self