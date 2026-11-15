from langchain_core.language_models	import BaseChatModel

from miaoli_bot.api		import get_root_config
from miaoli_bot.errors	import ClientNotFound, ModelNotFound, ProviderNotFound

from ..utils	import get_client_cls


def build_client(provider_name: str, model_name: str) -> BaseChatModel:
	
	"""构建 BaseChatModel"""
	
	llm_config			= get_root_config().llm
	providers_mapping	= {pv.name: pv for pv in llm_config.providers}
	
	# 拿 provider 对象
	if (provider := providers_mapping.get(provider_name)) is None:
		raise ProviderNotFound(f"供应商 '{provider_name}' 未配置")
	
	# 通过 provider 对象 拿 model 对象
	models_mapping	= {md.name: md for md in provider.models}
	if (model := models_mapping.get(model_name)) is None:
		raise ModelNotFound(f"供应商 '{provider_name}' 未配置 '{model_name}' 模型")
	
	# 通过 provider 对象声明的 client 拿 BaseChatModel 类
	if (client_cls := get_client_cls(provider.client)) is None:
		raise ClientNotFound(f"{provider.client} 没有相应的适配器")
	
	# 构建 BaseChatModel 实例
	client = client_cls(
		base_url	= provider.base_url,
		api_key		= provider.api_key,
		model		= model.name,
		max_tokens	= model.max_tokens
	)
	
	return client
