from langchain_anthropic	import ChatAnthropic

from langchain_core.language_models	import BaseChatModel

from langchain_deepseek	import ChatDeepSeek

from langchain_openai	import ChatOpenAI

from ..core		import SHARE_STORE
from ..consts	import PLUGIN_CONFIG
from ..models	import LLM, Provider
from ..errors	import ClientNotFound, ModelNotFound, ProviderNotFound

from typing	import Optional, Type, Union


CLIENT_MAPPING = {
	"deepseek": ChatDeepSeek,
	"openai": ChatOpenAI,
	"anthropic": ChatAnthropic,
}


def get_model_info() -> LLM:
	
	"""获取当前使用的模型信息"""
	
	config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	# PluginConfig 保证他们同时存在
	provider	= _get_provider(config.provider)
	model		= _get_model(config.model, provider)
	
	return model

def get_provider_info() -> Provider:
	"""获取当前使用的供应商信息"""
	return _get_provider(SHARE_STORE.recall(PLUGIN_CONFIG).provider)

def build_client(
	provider_name	: Optional[str] = None,
	model_name		: Optional[str] = None,
) -> BaseChatModel:
	
	"""构建 BaseChatModel"""
	
	config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	# 参数不传则 plugin_config 定义的
	provider_name	= provider_name or config.provider
	model_name		= model_name or config.model
	
	# 拿 provider 对象
	if (provider := _get_provider(provider_name)) is None:
		raise ProviderNotFound(f"供应商 '{provider_name}' 未配置")
	
	# 通过 provider 对象 拿 model 对象
	if (model := _get_model(model_name, provider)) is None:
		raise ModelNotFound(f"供应商 '{provider_name}' 未配置 '{model_name}' 模型")
	
	# 通过 provider 对象声明的 client 拿 BaseChatModel 类
	if (client_cls := _get_client_cls(provider.client)) is None:
		raise ClientNotFound(f"{provider.client} 没有相应的适配器")
	
	# 构建 BaseChatModel 实例
	client = client_cls(
		base_url	= provider.base_url,
		api_key		= provider.api_key,
		model		= model.name,
		max_tokens	= model.max_tokens
	)
	
	return client


def _get_provider(name: str) -> Union[Provider, None]:
	
	"""内部实现 获取 provider 对象"""
	
	config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	providers_mapping	= {pv.name: pv for pv in config.providers}
	provider			= providers_mapping.get(name, None)
	
	return provider

def _get_model(name: str, from_provider: Provider) -> Union[LLM, None]:
	
	"""内部实现 从 provider 获取 LLM 对象"""
	
	models_mapping	= {md.name: md for md in from_provider.models}
	model			= models_mapping.get(name, None)
	
	return model

def _get_client_cls(client: str) -> Union[Type[BaseChatModel], None]:
	"""内部实现 从 CLIENT_MAPPING 拿 BaseChatModel 类"""
	return CLIENT_MAPPING.get(client)