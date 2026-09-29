from pydantic	import BaseModel, Field, ConfigDict, model_validator, FilePath, DirectoryPath
from typing		import Optional, Self, List, Union
from tempfile	import gettempdir
from pathlib	import Path

import os


class LLM(BaseModel):
	name			: str	= Field(..., description="用于请求的模型名")
	context_window	: int	= Field(default=128000, description="上下文窗口")
	max_tokens		: int	= Field(default=4096, description="最大输出")

class Provider(BaseModel):
	name		: str		= Field(..., description="供应商名字")
	base_url	: str		= Field(..., description="请求的地址 不会拼路径")
	api_key		: str		= Field(..., description="鉴权密钥")
	models		: List[LLM] = Field(default_factory=list, description="模型列表")

class MemeConfig(BaseModel):
	is_enable	: bool				= Field(default=False, description="是否启用 meme")
	sqlite_path	: Optional[Path]	= Field(default=None, description="meme 的 sql 数据库路径")
	max_memes	: Optional[int]		= Field(default=None, description="最大meme的数量")
	
	@model_validator(mode="after")
	def check_path(self) -> Self:
		
		"""
		可以关闭+传路径
		但不能启用+不传路径
		"""
		
		if self.is_enable is True and not str(self.sqlite_path):
			raise ValueError("不能启用 meme 但不传数据库路径")
		
		return self

class AccountConfig(BaseModel):
	bot_id			: str = Field(..., description="机器人QQ号")
	root_id			: str = Field(..., description="管理员QQ号")
	bot_nickname	: str = Field(..., description="机器人昵称")
	root_nickname	: str = Field(..., description="管理员名称")

class OutputConfig(BaseModel):
	typing_speed		: Union[int, float]	= Field(default=0.01, description="打字时间 (一个字)")
	typing_speed_offset	: Union[int, float]	= Field(default=0, description="打字速度偏移")
	split_separator		: str				= Field(default="", description="输出分隔符")

class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")
	
	providers: List[Provider]	= Field(default_factory=list, description="供应商")
	
	session_dir		: DirectoryPath			= Field(default_factory=gettempdir, description="会话保存路径 默认使用临时路径")
	prompt_file		: Optional[FilePath]	= Field(default=None, description="系统提示词文件")
	system_prompt	: Optional[str] 		= Field(default=None, description="系统提示词")
	
	account_config	: AccountConfig	= Field(..., description="账号信息配置")
	meme_config		: MemeConfig	= Field(default_factory=MemeConfig, description="meme配置")
	output_config	: OutputConfig	= Field(default_factory=OutputConfig, description="AI输出配置")
	
	@model_validator(mode="after")
	def init_prompt(self) -> Self:
		
		"""prompt_file 优先"""
		
		if self.prompt_file is not None:
			self.system_prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self