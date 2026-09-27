from pydantic	import BaseModel, Field, ConfigDict, model_validator
from typing		import Optional, Self
from tempfile	import gettempdir
from pathlib	import Path
from copy		import deepcopy

import os


class LLM(BaseModel):
	name: str	= Field(..., description="用于请求的模型名")

class Provider(BaseModel):
	
	name		: str		= Field(..., description="供应商名字")
	base_url	: str		= Field(..., description="请求的地址 不会拼路径")
	api_key		: str		= Field(..., description="鉴权密钥")
	llm_models	: List[LLM] = Field(default_factory=list, description="模型列表")

class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")
	
	providers: List[Provider]	= Field(default_factory=list, description="供应商")
	
	session_dir		: str			= Field(default_factory=gettempdir, description="会话保存路径 默认使用临时路径")
	system_prompt	: Optional[str] = Field(default=None, description="系统提示词")
	prompt_file		: Optional[str]	= Field(default=None, description="系统提示词文件")
	
	
	@model_validator(mode="after")
	def init_prompt(self) -> Self:
		
		"""prompt_file 优先"""
		
		if self.prompt_file is not None:
			self.system_prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self