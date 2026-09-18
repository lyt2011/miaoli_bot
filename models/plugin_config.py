from pydantic	import BaseModel, Field, ConfigDict, model_validator
from typing		import Optional, Any, Self
from tempfile	import gettempdir
from pathlib	import Path
from copy		import deepcopy

import os


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(
		extra	= "allow",
	)
	
	model_id	: str	= Field(..., description="PI 模型")
	provider	: str	= Field(..., description="PI 模型供应商")
	session_dir	: str	= Field(default_factory=gettempdir, description="PI 会话保存路径 默认使用临时路径")
	
	system_prompt	: Optional[str] = Field(default=None, description="系统提示词")
	prompt_file		: Optional[str]	= Field(default=None, description="系统提示词文件")
	
	
	@model_validator(mode="after")
	def init_prompt(self) -> Self:
		
		"""prompt_file 优先"""
		
		if self.prompt_file is not None:
			self.system_prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self