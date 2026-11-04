from copy	import deepcopy
from typing	import Any, Dict

import pytest
import pydantic


# 一份完整且合法的 PluginConfig 参数 所有用例的基准
# 全用纯 dict / list 表示 方便 deepcopy 与局部覆盖 不要在用例里直接改它
PLUGIN_CONFIG_ARGS: Dict[str, Any] = {
	"provider"		: "the provider",
	"model"			: "the model",
	"providers"		: [
		{
			"name"		: "the provider",
			"base_url"	: "http://a.com/v1",
			"api_key"	: "sk-abc",
			"client"	: "deepseek",
			"models"	: [
				{
					"name"				: "the model",
					"context_window"	: 128000,
					"max_tokens"		: 4096,
					"support_visions"	: ["text"],
				},
			],
		},
	],
	"account"		: {
		"bot_id"			: "123",
		"admin_id"			: "1234",
		"bot_nickname"		: "bot",
		"admin_nickname"	: "admin",
	},
	"checkpointer"	: {"database": "memory", "connect_to": None, "extra": {}},
	"sub_plugin"	: {"enable": False, "load_from": []},
	"channel"		: {"drain_timeout": 30.0},
}


def copy_plugin_config() -> Dict[str, Any]:
	"""复制一份完整配置 不再需要一直重写"""
	return deepcopy(PLUGIN_CONFIG_ARGS)

def test_checkpointer_config() -> None:
	
	"""
	检查 checkpointer 配置
	非内存且没有 connect_to 时能正确抛出错误
	三个数据库类型能被正确校验
	"""
	
	from miaoli_bot.models	import CheckpointerConfig
	
	config	= copy_plugin_config()
	cp		= config["checkpointer"]
	
	# 测试没有 connect_to 的非 memory 构造
	with pytest.raises(pydantic.ValidationError):
		CheckpointerConfig.model_validate({**cp, "database": "postgresql"})
	
	# 测试不存在的数据库构造
	with pytest.raises(pydantic.ValidationError):
		CheckpointerConfig.model_validate({**cp, "database": "invalid database"})
		
	# 测试三种数据库构建
	CheckpointerConfig.model_validate({**cp})
	CheckpointerConfig.model_validate({**cp, "database": "postgresql", "connect_to": "fxxk"})
	CheckpointerConfig.model_validate({**cp, "database": "sqlite", "connect_to": "fxxk"})

def test_llm_config() -> None:
	
	"""测试 LLM 构建"""
	
	from miaoli_bot.models	import LLM
	
	config	= copy_plugin_config()
	llm		= config["providers"][0]["models"][0]
	
	# 测试错误上下文长度
	with pytest.raises(pydantic.ValidationError):
		LLM.model_validate({**llm, "context_window": -1})
	
	# 测试错误最大输出token
	with pytest.raises(pydantic.ValidationError):
		LLM.model_validate({**llm, "max_tokens": -1})
	
	# 测试不支持的模态
	with pytest.raises(pydantic.ValidationError):
		LLM.model_validate({**llm, "support_visions": ["invalid vision"]})
	
	# 测试空模态
	with pytest.raises(pydantic.ValidationError):
		LLM.model_validate({**llm, "support_visions": []})
	
	# 测试正确数据构建
	LLM.model_validate(llm)

def test_account_config() -> None:
	"""测试 AccountConfig 构建"""
	from miaoli_bot.models	import AccountConfig
	AccountConfig.model_validate(copy_plugin_config()["account"])

def test_provider_config() -> None:
	"""测试 Provider 构建"""
	from miaoli_bot.models	import Provider
	Provider.model_validate(copy_plugin_config()["providers"][0])

def test_plugin_config() -> None:
	
	"""
	测试 PluginConfig
	错误模型配置时是否报错
	"""
	
	from miaoli_bot.models	import PluginConfig
	
	config = copy_plugin_config()
	
	# 测试空 providers
	with pytest.raises(pydantic.ValidationError):
		PluginConfig.model_validate({**config, "providers": []})
	
	# 测试不存在的 provider
	with pytest.raises(pydantic.ValidationError):
		PluginConfig.model_validate({**config, "provider": "invalid provider"})
	
	# 测不存在的 model
	with pytest.raises(pydantic.ValidationError):
		PluginConfig.model_validate({**config, "model": "invalid model"})
	
	# 完整构建测试
	PluginConfig.model_validate(config)