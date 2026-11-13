from string	import Template


# 单条内容被截断时的尾巴，$n 是丢弃的字符数
TRUNCATED_LABEL = "[TRUNCATED $n characters...]"
TRUNCATED_TEMPLATE = Template(TRUNCATED_LABEL)

# AIMessage.tool_calls 展开成一行时的形态，$name / $args 来自 ToolCall
TOOL_CALL_LABEL = "$name -> $args"
TOOL_CALL_TEMPLATE = Template(TOOL_CALL_LABEL)
