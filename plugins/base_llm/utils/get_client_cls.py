from langchain_core.language_models	import BaseChatModel

from ..consts	import CLIENT_MAPPING

from typing	import Type, Union


def get_client_cls(client: str) -> Union[Type[BaseChatModel], None]:
	"""从 CLIENT_MAPPING 拿 BaseChatModel 类"""
	return CLIENT_MAPPING.get(client)
