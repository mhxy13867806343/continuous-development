# continuous-development：会话管理与低额度同步扩展

> 完整目录包说明：本包已经按下列接入规则合并完成，不必再次手动接入或运行增量安装。下文的接入步骤供更新其他旧副本时参考；实际客户端能力仍需单独接通与验证。

交付版本：session-extension-v1；整理日期：2026-10-24。

## 这份包做了什么

本文件保留会话扩展的命令与设计说明；当前下载交付为**已接入的完整目录包**。保留原有 `help/h`、`always()`、`run(...)`、`Sub-agent`、动态技术栈和文档/Git 规则。

包含：五份运行规则、一份接入说明、配置样例、交接模板、只做解析/决策的 Python 脚本及单元测试。

**已实现的是本地命令解析与确定性策略计算。尚未实现/实测的是各客户端的会话适配器、控制器、定时器安装和自动推送执行器。** `execution: not_executed` 是脚本的真实输出，不代表功能已启动。Markdown 规则需要具有相应工具的 Codex/宿主执行；不能凭写了规则就操作其他应用。

本包未修改远程仓库，未接管用户电脑上的会话，未创建定时任务。本完整包以核对过的 GitHub 内容快照为基础；没有核实或更新 Gitee 当前内容，不能认定两个远程仓库已经同步。

## 默认方案

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `initial` | 20 | 首批接管的现存开发会话数；可用 `"all"` 接管授权范围内全部现存开发会话 |
| `limit` | 15 | 同一统计范围内允许保留的未归档主会话上限 |
| `rounds` | 15 | 每个会话达到此轮数后，停止追加新任务并准备换新；不是强制杀掉当前任务 |
| `scope` | `host` | 当前客户端/账户可核实范围；不是所有软件共享一个未经核实的总数 |
| `every` | `"5m"` | 定时同步检查周期，300 秒 |
| `threshold` | 1 | **剩余套餐额度**小于等于 1% 时进入低额度保护 |
| `on_low` | `"checkpoint-push-pause"` | 保存交接，安全推送可提交的成果，然后暂停新的模型任务 |

本方案将用户所说的“15 调”理解为 **15 轮对话**，与“最多 15 个会话”是两个独立参数。

`initial=20` 不是已发现 20 个会话的证据。运行时必须真实列出、分页去重并核实目标。

## 复制即可作为 Skill 指令的写法

以下为新增工作流约定；本完整目录已经接入规则和解析脚本，执行实际动作仍要求相应宿主工具可用。

### 接管现有会话与控制数量

```text
@continuous-development sessions(initial=20, limit=15, rounds=15)
```

从当前客户端可确认的开发会话中形成首批快照：先完成现有工作，不给达到轮数阈值的会话添加新业务任务；完成后保存交接并归档。首批尚未处理完时暂不补建，全部完成后再在上限内补位。

```text
@continuous-development sessions(initial="all", limit=15, rounds=15)
@continuous-development sessions(initial=25, limit=10, rounds=30)
@continuous-development sessions("status")
@continuous-development sessions("stop")
```

`stop` 停止本扩展的自动归档/补建管理，不强杀正在开发的任务；不影响原有 `stop()` 对定时续作的含义。

### 获取当前会话 ID、链接和交接 Markdown

```text
@continuous-development handoff()
@continuous-development handoff("codex://threads/01a16dcd-a970-7232-a17f-4fe891230c55")
```

无参数时读取当前宿主提供的真实会话身份；无法读取就明确报告，不从示例或旧记录猜测。
有参数时先解析并核实对应会话，不把传入 ID 自动视为当前会话。

### 查看进度

```text
@continuous-development open()
@continuous-development open("项目名称")
@continuous-development open("项目ID")
@continuous-development open("/本地/项目/路径")
@continuous-development open("codex://threads/01a16dcd-a970-7232-a17f-4fe891230c55")
```

这是只读进度查询。默认当前项目，可按项目 ID、名称、路径、已知会话 ID/链接解析。同名多个结果先列候选，不擅自选中。查不到应报告未找到。

返回已完成/总任务、百分比的计算依据、最近完成内容、当前任务、阻塞、分支、同步状态、会话数量和下一步。没有任务总量时百分比为“未知”，不是凭感觉写 80%。

### 每 5 分钟检查同步；剩余 1% 进入保护

```text
@continuous-development sync(every="5m", threshold=1, on_low="checkpoint-push-pause")
```

只使用当前项目已有且明确的上游。指定多个远程时：

```text
@continuous-development sync(every="5m", threshold=1, on_low="checkpoint-push-pause", remotes=["github","gitee"])
@continuous-development sync("status")
@continuous-development sync("stop")
```

`github`、`gitee` 必须是**当前项目已经配置的远程名称**。你提供的两个 continuous-development 仓库是 Skill 仓库，不是其他所有开发项目的上传目的地。

`sync()` 是本地 Git 同步检查，不是每 5 分钟发送一轮模型开发请求。需宿主支持该频率或安装本地调度器；Mac 可用 launchd。只有真实安装并读取验证成功后，才显示“已启用”。

### 一条一条调用，不把管理命令混在一起

本版每次只解析一个 `sessions/open/handoff/sync` 管理调用，避免只读和写入混跑。现有 `always()`、`run()`、`Sub-agent` 语法保持原样。

推荐初次接入顺序：`open()` → `sessions(...)` → `sync(...)`。实际能力未就绪时，不会因为命令解析成功就启动控制器。

## 工作机制

```text
真实枚举当前会话
    ↓
接管首批 20 个（或者配置数量）
    ↓
先完成旧任务；超过 15 轮标记待换新，不中断正在工作
    ↓
校验、保存交接、确认没有运行中的工具/子代理
    ↓
归档成功并复核
    ↓
首批清空后，按可用空位创建后续会话
    ↓
新会话读取交接，继续未完成目标/后续待办
```

14 个未归档会话时最多新增 1 个；从 15 个归档 10 个后最多新增 10 个。上限是上限，不是一定要开满 15 个。

推荐默认不在没有任何下一步任务时反复创建空对话。需要严格“一归档就补一个空对话”可设置 `create_empty_replacements=true`，但仍受首批清空与数量上限限制，空对话不会自动再次归档制造循环。

## 安全边界

- 达到 15 轮，不等于任务完成；模型回复结束也不等于业务任务完成。
- 阈值、数量、任务完成度、额度百分比，分别记录，不能混用。
- 未完成工作遇到低额度时保存并暂停，不把它归档为已完成。
- 归档不是删除；不能用删除会话/修改客户端内部数据库冒充归档。
- 没有宿主能力时显示 `unsupported` 或 `blocked_capability`；保留本地交接，不编造成功结果。
- 不自动购买额度、切换收费 API、强制 push、覆盖别人的工作。
- 会话交接和私有 ID 默认只在本地保存；不要自动上传完整聊天记录到公开仓库。

## 文件安装

保留现有已经生效的 Skill 目录，例如：

```text
~/.codex/skills/continuous-development/
```

将本包中的新规则及脚本合并进去，再按 `SESSION-INTEGRATION.md` 修改原入口。不要删除旧目录，不要把旧版 ZIP 整份覆盖到新仓库上。

### 自动接入现有 Skill（仅本地文件）

包内 `install_extension.py` 会检查现有文件中的唯一锚点，并保留原有功能。
默认只预览；检测到冲突、新文件已被修改、目标不匹配或符号链接时停止，不强行覆盖。
正式应用前自动把旧文件备份到 Skill 目录之外；失败时尽力回滚本次写入。

在解压后的 `continuous-development-session-extension` 目录打开终端：

```bash
# 先预览，不写文件
python3 install_extension.py --target "$HOME/.codex/skills/continuous-development"

# 确认预览后正式接入，本地备份由脚本创建
python3 install_extension.py --target "$HOME/.codex/skills/continuous-development" --apply
```

安装脚本只更新 Skill 文件，不 commit、不 push、不创建定时任务、不连接任何聊天应用。
脚本验证过测试夹具下的插入/回滚/幂等行为，用户机器上仍应先预览；有其他自定义改动导致锚点冲突时，按接入文档局部合并。

安装后**解析成功不等于运行时接通**。先在新会话使用 `open()` 测试只读路由；缺少宿主数据时应显示 unknown/unsupported。

测试只需要 Python 3.9+，没有第三方依赖：

```bash
python3 -m unittest discover -s tests -p 'test_lifecycle_policy.py' -v
python3 scripts/lifecycle_policy.py '@continuous-development sessions(initial=20, limit=15, rounds=15)'
```

最后一条命令只输出解析结果，不会真的接管会话。真实归档、新建、调度与推送，需要另外完成宿主接入验收。
