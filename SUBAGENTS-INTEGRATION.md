# Sub-agent 命令接入说明与验收清单

日期：2026-10-11  
目标仓库：`mhxy13867806343/continuous-development`  
交付性质：新增规则与接入文档；不包含 Git 提交、远程修改、运行时解析器或 GUI 插件。

## 一、与当前仓库的关系

本次对照读取的默认分支文件包括 `SKILL.md`、`invocation.md`、`orchestration.md` 和 `README.md`。现有入口统一加载八个规则文件，已有 `help/h`、`always()`、`run(...)`、`status()`、`stop()`；现有调度要求动态拆任务，不固定技术栈角色。

参考文件与读取时的内容 blob SHA：

| 文件 | blob SHA |
| --- | --- |
| `SKILL.md` | `56b7d6bbbda8b74791944c1918d31779d2554851` |
| `invocation.md` | `c909cae03e333b8f03fcbc81981d246afc760aa5` |
| `orchestration.md` | `773f9dbcc30fe6cb048341b3d77aac50233fba58` |
| `README.md` | `474debfd1ff76d9abf7c108e34adff62cff8cc2d` |

这些是文件内容标识，不是本次新增的提交，也不证明用户本地文件与远程一致。仓库后续有更新时，应合并下列局部补充，不要用旧文件整份覆盖。

建议只新增 `subagents.md`，再局部调整上面的四个文件。`git.md` 等其他规则不需要在本次重写。

## 二、目录

```text
continuous-development/
├── SKILL.md                  # 增加引用与命令路由优先规则
├── invocation.md             # 增加 Sub-agent 入口与帮助
├── subagents.md              # 新增：名称选择、默认全选、交互选择
├── orchestration.md          # 加入“只调度选中名单”限制
├── repository.md
├── validation.md
├── typesafe.md
├── documentation.md
├── git.md
├── quota-safety.md
├── README.md                 # 补充使用示例和能力边界
└── LICENSE
```

此处的 `subagents.md` 是主 Skill 的规则文件，不是名为 subagents 的独立 Skill，更不是子代理配置名单。保留当前已经生效的安装目录即可，不需要因为新增这个文件就迁移安装位置。

## 三、`SKILL.md` 的局部补充

在现有规则加载列表后增加：

```markdown
9. `subagents.md`
```

在 `## Main behavior` **之前**增加下面的段落。不能只加文件引用，否则旧的“immediately inspect / begin”规则可能让只读或选择命令直接进入开发循环。

```markdown
## Command routing takes precedence

Read all rule files relative to this SKILL.md, then classify the invocation
before starting repository development or causing side effects.

Follow `subagents.md` when a Sub-agent selector is present. It governs
agent selection, parameter validation, and interactive confirmation;
`orchestration.md` governs task scheduling within the resolved selection.

Help and status are read-only. A pending, cancelled, empty, invalid, or
unavailable Sub-agent selection must not fall through to the development
loop, commit/push operations, or automation creation.

Apply the generic Main behavior below only after an execution command
has been recognized, its selection is resolved, and the user's current
constraints permit execution.

Current explicit user restrictions take precedence. Selecting agents does
not grant new permissions or override a no-edit/no-commit/no-push request.
```

可在现有 YAML `description` 的末尾补充 `Supports Sub-agent selection.`，但不要把 `Sub-agent` 加进 Skill 的 `name`。

## 四、`invocation.md` 的局部补充

在 `## Supported commands` 下新增此节：

```markdown
### Sub-agent selection

Follow `subagents.md` for the complete selection grammar and safeguards.

Supported forms after the continuous-development skill invocation:

- `Sub-agent` or `Sub-agent()` — select all currently callable agents.
- `Sub-agent(name)` — select one agent by its actual callable name.
- `Sub-agent(a,b,c)` — select multiple agents.
- `Sub-agent([a,b,c])` — equivalent list form.
- `Sub-agent a,b,c` — equivalent comma-separated form.
- `Sub-agent .` or `Sub-agent(.)` — request interactive selection first.

Names in examples are placeholders, not built-in agents.
Use ` -- ` before an additional task objective when this selector is used.

Sub-agent alone starts the current-session continuous workflow without
changing automations. To combine it with an existing execution mode, put
that mode first: `always() Sub-agent(a,b)` or `run(2h) Sub-agent(a,b)`.

Parse and validate the selection before development or automation changes.
Never interpret invalid input, cancellation, or an unanswered picker as all.
Do not claim that Markdown itself installs an input popup or a native command.
```

在现有 `## Command parsing` 开头增加：

```markdown
For invocations containing Sub-agent, resolve command routing and selection
according to `subagents.md` before applying the default development behavior.

`help Sub-agent`, `h Sub-agent`, and `help() Sub-agent` show selection help.
`status() Sub-agent` inspects available and selected agents without spawning.
`stop() Sub-agent(...)` is unsupported; stop() retains its automation meaning.

For execution modes, use the order:
[always() or run(...), optional] Sub-agent [selection, optional] [ -- objective]

When help/h lists commands, include Sub-agent forms, example names, the
all-versus-concurrency distinction, and the conditional picker behavior.
```

不要删除现有 `help/h`、`always()`、`run(...)`、`status()` 或 `stop()` 实现说明。

## 五、`orchestration.md` 的局部补充

在 `## Dynamic workstreams` 之前增加：

```markdown
## Selected-agent boundary

When a Sub-agent selector is present, follow `subagents.md` and resolve
selection before task dispatch. Waiting for the user's explicit selection
is a valid pause even in always() mode.

Use only the resolved callable agent names. Do not add unselected agents,
substitute a generic agent for an invalid name, or bypass the selection
through nested delegation. The main agent remains the coordinator.

All selected agents must have an accounted-for state. Selection is not
concurrency: queue suitable tasks when the safe/runtime concurrency cap
is lower than the number of selected agents. Do not truncate the selection
or invent tasks to force every selected agent to run.

The existing dynamic-workstream and validation rules continue to apply.
Only the main agent integrates Git changes; preserve current user restrictions.
```

## 六、可复制到 `README.md` 的使用说明

以下内容可放在现有“使用”章节内：

````markdown
### 指定子代理：Sub-agent

`Sub-agent` 是本 Skill 的提示词约定，使用当前环境实际可调用的代理名称，
不创建同名代理，也不把 `.md` 文件当成代理。

```text
@continuous-development Sub-agent
@continuous-development Sub-agent(a)
@continuous-development Sub-agent(a,b,c)
@continuous-development Sub-agent([a,b,c])
@continuous-development Sub-agent a,b,c
@continuous-development Sub-agent .
```

不传名称表示全部可用子代理进入选择集合；并不表示全部同时启动。
指定名称时只在所选名单内分配任务，超出安全并发数的任务排队执行。
`a/b/c` 是示例，使用前换成实际名称。

带目标：

```text
@continuous-development Sub-agent(a,b) -- 优先修复测试失败
```

与原有模式组合：

```text
@continuous-development always() Sub-agent(a,b) -- 继续当前项目
@continuous-development run(2h) Sub-agent([a,b]) -- 继续现有 backlog
```

查看可用名单：

```text
@continuous-development status() Sub-agent
```

在使用 `$` 提及 Skill 的界面，将前缀换为 `$continuous-development`。

`Sub-agent .` 在发送后请求选择：有可用交互工具时使用宿主支持的选择界面，
否则显示编号列表，等待回复 `1,3`、实际名称、`全部` 或 `取消`。
选择未确认前不改代码、不提交、不创建定时任务。

仅导入 Markdown 不能使输入框在键入 `.` 时立即弹窗；这种输入补全需要宿主支持。
详见 [子代理选择规则](./subagents.md)。
````

## 七、功能边界：文档、原生代理和弹窗

本节为核对过的外部能力说明，与上面的新增命令约定分开。

**Skill 提及。** OpenAI 官方文档把 Skill 定义为指令及可选资源，并说明 ChatGPT 的 `@` 提及和 Codex CLI/IDE 的 `$` 提及。自定义的 `Sub-agent(...)` 是本仓库新增解释规则，不是官方已经注册的函数。[官方 Skill 文档](https://developers.openai.com/codex/skills/)

**代理配置。** 官方本地 Codex 子代理文档说明，自定义代理可来自 `.codex/agents/` 或 `~/.codex/agents/` 的 TOML 配置，代理的 `name` 字段是调用名称来源。运行环境或版本可能不同，所以本扩展优先使用运行时有效目录，而不是读取本 Skill 的文件名来猜代理。[官方子代理文档](https://developers.openai.com/codex/subagents/)

**选择界面。** 官方 App Server 文档描述了用户输入请求与客户端响应机制。这支持“有对应工具与客户端实现时请求用户选择”的设计，但不能据此断言每个 Codex++ 界面都有任意多选弹窗，也不能断言 Markdown 能监听未提交的键盘输入。[官方 App Server 文档](https://developers.openai.com/codex/app-server/)

本功能分为两层交付：文档层负责发送后的识别、名单约束与对话交互；真正的输入时自动补全、搜索式多选、鼠标勾选与点击回填需要客户端/插件实现。当前包只交付文档层规则，不包含上述 UI 实现。

## 八、验收用例（待在实际环境执行）

以下测试中的 `a/b/c` 由测试夹具或人工预先设置为可调用名称；不要把它们当成当前用户已经安装的代理。

| 编号 | 输入或情形 | 预期结果 |
| --- | --- | --- |
| 01 | `Sub-agent` | 选择完整可用集合；并发另行调度 |
| 02 | `Sub-agent()` | 同上 |
| 03 | `Sub-agent(a)` | 仅 a 进入名单 |
| 04 | `Sub-agent(a,b,c)` | 顺序解析 a、b、c |
| 05 | `Sub-agent([a,b,c])` | 与 04 等价 |
| 06 | `Sub-agent(["a","b"])` | 解析字符串名单，不执行表达式 |
| 07 | `Sub-agent a,b,c` | 与 04 等价 |
| 08 | `Sub-agent(a,a,b)` | 解析到 a、b，去重保序 |
| 09 | `Sub-agent(a，b)` | 中文逗号作为分隔符 |
| 10 | `Sub-agent(a,unknown)` | 整次不派发；报告 unknown，不静默只调用 a |
| 11 | `Sub-agent([])` / `Sub-agent("")` | 空选择错误，不变成全选 |
| 12 | `Sub-agent(a,,b)` / `Sub-agent(a,)` | 格式错误，不派发 |
| 13 | `Sub-agent(a,b` | 括号错误，不派发 |
| 14 | `Sub-agent a,b,...` | 省略号不是代理名，不继续猜测 |
| 15 | `Sub-agent .`，工具可交互 | 请求选择；确认前零开发副作用 |
| 16 | `Sub-agent .`，无交互工具 | 编号列表；不声称弹窗已打开 |
| 17 | 选择时回复 `1,3` | 按展示快照解析，确认可用后执行 |
| 18 | 选择时回复“取消”或没有回答 | 不默认全选、不启动、不创建定时任务 |
| 19 | `Sub-agent(a,.)` | 混合选择错误，不启动 |
| 20 | `help Sub-agent` | 仅帮助，不扫描项目或运行代理 |
| 21 | `status() Sub-agent` | 只读查看名单与状态 |
| 22 | `stop() Sub-agent(a)` | 提示不支持的组合，不误停任务 |
| 23 | `always() Sub-agent(a,b) -- 继续现有 backlog` | 只使用 a/b；续作设置需真实能力与成功证据 |
| 24 | `always() Sub-agent .` 后取消 | 不因 always() 而跳过确认，不建定时任务 |
| 25 | 选中五项，实际并发上限为二 | 适合任务分批；不截断为两项，不突破上限 |
| 26 | 所选代理仅可读，任务要求写代码 | 不扩大权限或偷偷替换代理 |
| 27 | `Sub-agent(a) -- 仅审查，不改代码，不提交` | 当前约束覆盖通用开发/Git步骤 |
| 28 | 子代理目录未知或为空 | 如实报告；不伪造“全部代理已启动” |
| 29 | 只有普通模型工具，没有子代理启动能力 | 不把串行角色扮演报告成真实多代理 |
| 30 | 续作时所选名称已删除 | 不自动扩大为全部，不保存原始 `.` 重复等待 |
| 31 | 新规则文件存在但入口未引用 | 应识别接入未完成，不能只凭文件存在判定功能生效 |
| 32 | 只是输入框内键入 `.`、尚未发送 | 无客户端扩展时不要求出现原生弹窗 |

## 九、给 Codex 的接入任务文本与验证步骤

### 9.1 快速接入提示词（可直接复制给 Codex）

在 Codex 的普通对话里直接发送：

```text
请帮我接入 continuous-development 的子代理选择功能。
Skill 目录：
~/.codex/skills/continuous-development/
我已经把以下两个文件放进这个目录：
- subagents.md
- SUBAGENTS-INTEGRATION.md
请先读取 SUBAGENTS-INTEGRATION.md 和 subagents.md，
再检查当前目录里的现有文件。
先备份需要修改的文件，备份放到 Skill 目录之外，
然后按照接入说明，仅局部更新：
- SKILL.md
- invocation.md
- orchestration.md
- README.md
要求：
1. 保留现有功能和我的其他修改，不用旧版本整份覆盖。
2. 在 SKILL.md 中接入 subagents.md。
3. 增加 Sub-agent 的命令说明、参数解析和帮助内容。
4. 先解析命令、确认子代理选择，再进入开发循环。
5. Sub-agent . 必须等待用户选择；取消或无效输入不能默认全选。
6. 没有真实选择界面能力时，使用对话编号列表，不声称已实现弹窗。
7. 不把 SUBAGENTS-INTEGRATION.md 加入运行时规则加载列表。
本次只做 Skill 文档接入：
- 不启动当前项目的持续开发
- 不启动子代理
- 不创建或修改定时任务
- 不修改模型和代理配置
- 不执行 git commit、push 或创建 PR
完成后检查文件引用、命令示例和规则是否一致，
告诉我修改了哪些内容，以及哪些功能尚未实测。
```

### 9.2 接入后第一步：安全只读冒烟测试

接入后在新对话里执行：

```text
@continuous-development help Sub-agent
```

- **预期行为**：仅打印 Sub-agent 选择语法与使用示例，不启动开发循环，不扫描修改代码，不创建定时任务。
- **边界说明**：展示帮助代表规则与解析接入成功，仍不代表原生输入框弹窗或子代理多进程并发已经实测完成。

## 十、验证声明

本交付是根据现有仓库结构整理的规则与验收设计。可以检查 Markdown 结构、引用和示例一致性；没有在用户的 Codex/Codex++ 中运行命令解析、原生多选 UI 或多代理执行测试。文件存在、规则读取成功、代理成功启动、弹窗成功展示应分别验证，不能相互替代。
