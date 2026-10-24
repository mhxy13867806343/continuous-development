# Host Adapters：跨客户端的能力边界

本文件把“统一工作流”与“各软件能否真正执行”分开。`cc` 在这里按 Claude Code 解释。

## 标准能力（适配器合同，不是现有 SDK 的虚构函数）

下面是本扩展要求的抽象能力名，不表示每个客户端已有同名 API：

- identity：当前 host/account/project/session 身份；平台原生来源链接。
- list_sessions：分页、归档、父子关系、工作目录、可靠运行状态与观测时间。
- read_session：只读上下文/任务状态，保护敏感信息。
- create_session：真实新建且返回 ID，支持操作去重或可可靠对账。
- archive_session：归档不删除，返回并可重新读取验证。
- execution_state：主任务、工具、子代理、审批是否仍在运行。
- quota：适用于当前任务的套餐额度与时间信息。
- scheduler：支持的时间间隔、安装/停用/查询及任务身份。

每个能力标注 supported / unsupported / unknown。能力缺失不使用私有数据库写入、伪造链接、模拟工具回执补齐。

## Codex

官方 App Server 文档列出了 thread/start、thread/list、thread/read、thread/archive 与 account/rateLimits/read。具体 schema 应通过安装版本的文档/生成 schema 核实。

thread/archive 可能联动后代线程，所以归档前要核实子代理工作状态。启动一个独立 App Server 进程不等于掌握 GUI 里所有任务的实时状态，必须验证连接到正确账户/存储/宿主，不能仅凭本进程看不到 loaded thread 判断另一个 GUI 会话已空闲。

可用原生接口不等于当前 ChatGPT 对话中已连接这些权限。旧示例里 codex://threads/... 是用户提供的客户端链接形式；保存实际宿主产生的 URL，不把硬编码 scheme 当成所有版本的承诺。

## Claude Code / cc

官方会话管理支持按 ID 恢复与分支。跨会话使用其实际 ID 和官方恢复方式；这不证明存在一个可让外部 Skill 任意归档全部 Desktop 聊天的接口。

CLI 本地会话、Desktop 会话和云端会话不要混为同一管理范围。未验证 archive/create/list 端到端能力时降级为生成 Markdown 交接与人工操作，不宣称自动归档成功。

## Antigravity

官方 CLI 文档描述按工作目录保存/恢复及 fork；CLI 能力不能自动套用到 IDE 的聊天侧栏。

本包不假定有通用归档 API、计费百分比接口或原生 URI scheme。先检测安装版本和真实提供的能力，不能写死一个不存在的 URL/API。

## Kiro

官方 CLI 会话文档包含按 ID 恢复、会话列表和 /chat new 等方式；会话导出归档包不是“从 UI 归档旧聊天”，删除会话也不是归档。

实际 CLI/IDE/云端能力分别检测。不要把 backing workflow/subagent 会话作为用户主会话重复计数。

## 默认范围和全局上限

默认仅当前 host/account 的授权范围，15 是该范围内主会话的数量上限。如果要四个应用总和≤15，必须显式配置 all-hosts scope、四个可用适配器和共享原子容量管理；任何一方清单不完整则不能保证跨应用总量。

主会话可以由子代理、任务和多个 Git worktree 组成；不能把这些数量与界面主会话数混算。

## 本次实际能力状态

- 已读取 GitHub 最新入口、调用规则和参数解析脚本。
- Gitee 内容未成功获取，未判断与 GitHub 是否一致。
- 当前电脑桥接返回离线，因此没有读取/归档/新建任何用户本地会话。
- 本包只提供规则、适配合同和只读策略计算，不内置这四种应用的生产适配器。

参考依据见 docs/SOURCES.md。接口支持情况必须在安装环境重新核实，不将文档参考当运行成功证明。
