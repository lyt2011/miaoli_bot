from pydantic	import BaseModel, Field, ConfigDict, model_validator, FilePath, DirectoryPath
from typing		import Optional, Self, Dict
from tempfile	import gettempdir
from pathlib	import Path

from .provider		import Provider
from .account		import Account
from .output		import OutputConfig
from .sub_plugin	import SubPluginConfig
from .check_pointer	import CheckPointerConfig


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")
	
	providers: Dict[str, Provider]	= Field(default_factory=dict, description="供应商")
	
	session_dir		: DirectoryPath			= Field(default_factory=gettempdir, description="会话保存路径 默认使用临时路径")
	prompt_file		: Optional[FilePath]	= Field(default=None, description="系统提示词文件")
	system_prompt	: Optional[str] 		= Field(default=None, description="系统提示词")
	
	account			: Account				= Field(..., description="账号信息配置")
	output			: OutputConfig			= Field(default_factory=OutputConfig, description="AI输出配置")
	checkpointer	: CheckPointerConfig	= Field(default_factory=CheckPointerConfig, description="check_pointer 数据库配置")
	sub_plugin		: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	
	@model_validator(mode="after")
	def init_prompt(self) -> Self:
		
		"""prompt_file 优先"""
		
		if self.prompt_file is not None:
			self.system_prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self