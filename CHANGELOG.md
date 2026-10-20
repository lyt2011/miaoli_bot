# Changelog

本项目所有重要变更均记录在此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循语义化版本（[SemVer](https://semver.org/lang/zh-CN/)）。

每个版本的完整记录单独存放在 [`CHANGELOG/`](CHANGELOG/) 目录下（文件名 `v<版本号>.md`），
本文件只保留索引：**版本号 + 日期 + 一句话摘要 + 链接**。

> **发新版时**：新建 `CHANGELOG/v<版本号>.md`（格式参照上一版），并在下方索引**顶部**插入一行。

## 索引

- [v0.25.1](CHANGELOG/v0.25.1.md) — 2026-10-21 — 新增 intent_recognition 子插件，按规则匹配末条消息注入意图提示词
- [v0.25.0](CHANGELOG/v0.25.0.md) — 2026-10-20 — meme_ops 配置拆成 database / help_doc 子配置，节点改名 inject_doc（破坏性）
- [v0.24.0](CHANGELOG/v0.24.0.md) — 2026-10-20 — meme_ops 提示词外置成文件，enable 真正生效（破坏性）
- [v0.23.1](CHANGELOG/v0.23.1.md) — 2026-10-20 — 移除压缩守卫，修掉其防御过度的问题
- [v0.23.0](CHANGELOG/v0.23.0.md) — 2026-10-20 — context_compactor 配置分层，修复二次压缩守卫从未生效与压缩节点必抛 NameError（破坏性）
- [v0.22.3](CHANGELOG/v0.22.3.md) — 2026-10-20 — meme_ops 新增 inject_helper 节点，注入表情包使用提示
- [v0.22.2](CHANGELOG/v0.22.2.md) — 2026-10-20 — 修复人设提示词从未进入上下文，新增 inject_soul 节点注入 soul 段
- [v0.22.1](CHANGELOG/v0.22.1.md) — 2026-10-20 — 补齐 should_compact 缺失的 Abort 导入，二次压缩拦截此前从未生效
- [v0.22.0](CHANGELOG/v0.22.0.md) — 2026-10-20 — 图管线抽出为独立包 miaoli_pipeline、提示词改用 SectionPatch 分段通道、压缩拆成三段事件（破坏性）
- [v0.21.0](CHANGELOG/v0.21.0.md) — 2026-10-19 — qq_adapter 更名 ob11_adapter、根配置改回 List[Provider] + List[LLM]、新增 miaoli_bot_adapter 子插件（破坏性）
- [v0.20.0](CHANGELOG/v0.20.0.md) — 2026-10-18 — 新增 api 门面层，子插件不再直接操作 SHARE_STORE（破坏性）
- [v0.19.1](CHANGELOG/v0.19.1.md) — 2026-10-18 — 修复提示词里「叫对方雑魚」与「直接称呼名字」的人设冲突
- [v0.19.0](CHANGELOG/v0.19.0.md) — 2026-10-18 — mcp_adapter_demo 转正为 mcp_adapter，reusable 上提到 server 层，提示词更新到 v1.6（破坏性）
- [v0.18.2](CHANGELOG/v0.18.2.md) — 2026-10-17 — 修复 tool_attachment_fixer 的 flush 时机缺陷（issue #1），清理冗余守卫
- [v0.18.1](CHANGELOG/v0.18.1.md) — 2026-10-17 — 文档版：记录 tool_attachment_fixer 的两个缺陷，本版无代码改动
- [v0.18.0](CHANGELOG/v0.18.0.md) — 2026-10-17 — 子插件配置外置 + 权限表精简 + 两处插件改名
- [v0.17.4](CHANGELOG/v0.17.4.md) — 2026-10-16 — 修复「整条图流水线静默失败」
- [v0.17.3](CHANGELOG/v0.17.3.md) — 2026-10-16 — 修复 tool_attachment_fixer 把图片消息插进 ToolMessage 段中间导致的 400
- [v0.17.2](CHANGELOG/v0.17.2.md) — 2026-10-16 — 并发冲突的最简修复：on_message 按 session_id 加 asyncio.Lock
- [v0.17.1](CHANGELOG/v0.17.1.md) — 2026-10-16 — 提示词资产更新：新增 prompt_v1.5.md，显著压住「说几个字就输出一大串文本」的倾向
- [v0.17.0](CHANGELOG/v0.17.0.md) — 2026-10-16 — 架构重构：qq_bot → qq_adapter（纯解析 adapter）+ 拆出 qq_platform_tools；解析子系统整体迁入 adapter；事件以「字典」进图，而不是把原始 ncatbot 对象塞进 runtime.context；发送从图内节点移回 core 的 main.py
- [v0.16.1](CHANGELOG/v0.16.1.md) — 2026-10-07 — 主 README 同步，本版无代码改动
- [v0.16.0](CHANGELOG/v0.16.0.md) — 2026-10-07 — read_image 支持更多图片格式，并把格式名单写进文档
- [v0.15.0](CHANGELOG/v0.15.0.md) — 2026-10-07 — 新增 send_poke 戳一戳工具，base_platform_tools 目录结构对齐其他子插件，PluginConfig 移除 session_dir
- [v0.14.1](CHANGELOG/v0.14.1.md) — 2026-10-06 — 补上 web_search 的权限声明，并把服务器部署的密钥配置收口
- [v0.14.0](CHANGELOG/v0.14.0.md) — 2026-10-06 — 新增 web_search 子插件（LangSearch 联网搜索），并把 7 个工具函数签名里的默认值全部去掉
- [v0.13.0](CHANGELOG/v0.13.0.md) — 2026-10-06 — 工具附件修复从 base_nodes 拆出、独立成子插件 tool_attachment_fixer（破坏性）
- [v0.12.0](CHANGELOG/v0.12.0.md) — 2026-10-05 — 上下文压缩从 base_nodes 拆出、独立成子插件 context_compactor；GraphState 里「每轮用完即丢」的 6 个键改用 UntrackedValue（破坏性）
- [v0.11.0](CHANGELOG/v0.11.0.md) — 2026-10-04 — 补上 0.10.0 留下的缺口：新增 base_topology 子插件，图重新可端到端跑通
- [v0.10.0](CHANGELOG/v0.10.0.md) — 2026-10-04 — GraphPipeline 重构：拓扑从「静态边」改为「事件节点 + 主动跳转」，控制流从异常改为返回值（破坏性）
- [v0.9.12](CHANGELOG/v0.9.12.md) — 2026-10-03 — 修复 GraphPipeline 增量归约不满足结合律的 bug（0.9.11 及之前的已发布代码里潜伏），并新增两个坏历史修复子插件
- [v0.9.11](CHANGELOG/v0.9.11.md) — 2026-10-02 — LLM 实例改为图内按需创建，并补齐这轮重构留下的坑
- [v0.9.10](CHANGELOG/v0.9.10.md) — 2026-10-01 — _dispatch 加错误处理，并新增「停止分发」信号 PipelineStopDispatch
- [v0.9.8](CHANGELOG/v0.9.8.md) — 2026-10-01 — 发送循环加调试日志
- [v0.9.7](CHANGELOG/v0.9.7.md) — 2026-10-01 — 修复「未设置分隔符时回复被逐字拆成 N 条消息」
- [v0.9.6](CHANGELOG/v0.9.6.md) — 2026-10-01 — 新增 tool_permission_manager 子插件 —— 工具级权限控制
- [v0.9.5](CHANGELOG/v0.9.5.md) — 2026-10-01 — 子插件文档补齐（第二份）
- [v0.9.4](CHANGELOG/v0.9.4.md) — 2026-10-01 — image 段解析新增 is_meme，并把它收窄到 QQ 平台（同时更名）
- [v0.9.3](CHANGELOG/v0.9.3.md) — 2026-10-01 — 把三个「直接 import 却靠传递依赖混进来」的包正式声明
- [v0.9.2](CHANGELOG/v0.9.2.md) — 2026-10-01 — 补齐 aiofiles 依赖声明
- [v0.9.1](CHANGELOG/v0.9.1.md) — 2026-10-01 — meme 子系统的 sqlite 驱动由 rapsqlite 换成 aiosqlite
- [v0.9.0](CHANGELOG/v0.9.0.md) — 2026-10-01 — checkpointer 真正接线（本次为架构级新增）
- [v0.8.3](CHANGELOG/v0.8.3.md) — 2026-10-01 — meme 子系统整体迁出主包
- [v0.8.2](CHANGELOG/v0.8.2.md) — 2026-10-01 — 本次为插件化拆分（架构级变更）
- [v0.8.1](CHANGELOG/v0.8.1.md) — 2026-09-29 — 本版本含破坏性更名
- [v0.8.0](CHANGELOG/v0.8.0.md) — 2026-09-29 — 本版本为破坏性重构
- [v0.7.0](CHANGELOG/v0.7.0.md) — 2026-09-18 — models/plugin_config.py —— PluginConfig（pydantic v2 配置模型）
- [v0.6.0](CHANGELOG/v0.6.0.md) — 2026-09-18 — 插件配置化建会话（config.yaml + main.py create_pi_factory）
- [v0.5.4](CHANGELOG/v0.5.4.md) — 2026-09-17 — pi_bridge 依赖下限提到 >=0.6.0
- [v0.5.3](CHANGELOG/v0.5.3.md) — 2026-09-17 — 插件命令被当作普通对话、机器人重复回复
- [v0.5.2](CHANGELOG/v0.5.2.md) — 2026-09-16 — close_sessions 关闭流程重构
- [v0.5.1](CHANGELOG/v0.5.1.md) — 2026-09-16 — PiSessionManager 高并发用例
- [v0.5.0](CHANGELOG/v0.5.0.md) — 2026-09-16 — core/pi_session_manager.py — PiSessionManager
- [v0.4.0](CHANGELOG/v0.4.0.md) — 2026-09-16 — 新工具 delete_qq_message
- [v0.3.3](CHANGELOG/v0.3.3.md) — 2026-09-15 — PiClient.is_streaming 只读属性
- [v0.3.2](CHANGELOG/v0.3.2.md) — 2026-09-15 — 插件入口类改名为 MiaoLiBot
- [v0.3.1](CHANGELOG/v0.3.1.md) — 2026-09-15 — errors/ 异常模块
- [v0.3.0](CHANGELOG/v0.3.0.md) — 2026-09-14 — 消息段解析扩展
- [v0.2.0](CHANGELOG/v0.2.0.md) — 2026-09-13 — message 正文解析接入主流程
- [v0.1.1](CHANGELOG/v0.1.1.md) — 2026-09-13 — 重构中间态（WIP）版本：责任链节点全面改名，message 解析尚未接入主流程
- [v0.1.0](CHANGELOG/v0.1.0.md) — 2026-09-12 — 初始提交 de11062

## 历史提交链接

早期版本（拆分前）在 CHANGELOG 里用链接定义指向 GitHub 的 commit / compare，
现作为提交哈希的记录保留：

- `0.5.2` — https://github.com/lyt2011/miaoli_bot/compare/d1863eb...main
- `0.5.1` — https://github.com/lyt2011/miaoli_bot/compare/5b4140b...main
- `0.5.0` — https://github.com/lyt2011/miaoli_bot/compare/50a3b2e...main
- `0.4.0` — https://github.com/lyt2011/miaoli_bot/commit/50a3b2e
- `0.3.3` — https://github.com/lyt2011/miaoli_bot/compare/f612505...main
- `0.3.2` — https://github.com/lyt2011/miaoli_bot/compare/4ffdf61...f612505
- `0.3.1` — https://github.com/lyt2011/miaoli_bot/compare/ebb8d53...4ffdf61
- `0.3.0` — https://github.com/lyt2011/miaoli_bot/commit/ebb8d53
- `0.2.0` — https://github.com/lyt2011/miaoli_bot/compare/e610876...55cb08f
- `0.1.1` — https://github.com/lyt2011/miaoli_bot/compare/de11062...e610876
- `0.1.0` — https://github.com/lyt2011/miaoli_bot/commit/de11062
