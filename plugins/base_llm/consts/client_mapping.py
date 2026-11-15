from langchain_anthropic	import ChatAnthropic

from langchain_deepseek	import ChatDeepSeek

from langchain_openai	import ChatOpenAI


CLIENT_MAPPING = {
	"deepseek": ChatDeepSeek,
	"openai": ChatOpenAI,
	"anthropic": ChatAnthropic,
}
