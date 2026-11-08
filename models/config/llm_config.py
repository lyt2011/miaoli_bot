from pydantic	import BaseModel, Field, model_validator

from .provider_config	import LLM, Provider, ThinkingEffort

from typing	import Dict, List, Self


class LLMConfig(BaseModel):
	
	model			: str				= Field(..., description="将要使用的模型")
	provider		: str				= Field(..., description="将要使用的供应商")
	thinking_effort	: ThinkingEffort	= Field(..., description="设置模型的思考强度")
	
	providers	: List[Provider]	= Field(..., description="供应商", min_length=1)
	
	@model_validator(mode="after")
	def check_provider_and_model(self) -> Self:
		
		"""检查供应商与模型的配置"""
		
		providers: Dict[str, Provider] = {p.name: p for p in self.providers}
		if self.provider not in providers:
			raise ValueError(f"供应商 '{self.provider}' 未配置")
		
		models: Dict[str, LLM]	= {model.name: model for model in providers[self.provider].models}
		if self.model not in models:
			raise ValueError(f"供应商 '{self.provider}' 未配置 '{self.model}' 模型")
		
		thinking_efforts = models[self.model].thinking_efforts
		if self.thinking_effort not in thinking_efforts:
			raise ValueError(f"{self.provider}/{self.model} 只支持 {list(thinking_efforts)}: 接收到 {self.thinking_effort}")
		
		return self
