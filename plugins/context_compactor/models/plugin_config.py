from pydantic	import BaseModel, Field, FilePath, PrivateAttr
from typing		import Optional

from .calculate_config	import CalculateConfig


OPTIONAL_PATH	= Optional[FilePath]


class PluginConfig(BaseModel):
	
	enable: bool = Field(default=False, description="是否启用该插件")
	
	keep_count: int	= Field(default=5, description="最多保留多少条消息")
	
	encoding	: str			= Field(default="utf-8", description="指定提示词编码")
	prompt_file	: OPTIONAL_PATH	= Field(default=None, description="压缩时使用的提示词")
	
	calculate: CalculateConfig	= Field(default_factory=CalculateConfig, description="token计算配置")
	
	# 被加载后的文本提示词
	_prompt: Optional[str] = PrivateAttr(default=None)
	
	
	@property
	def prompt(self) -> Optional[str]:
		
		"""懒加载提示词"""
		
		if self.prompt_file is not None and self._prompt is None:
			self._prompt = self.prompt_file.read_text(encoding=self.encoding)
		
		return self._prompt