# continuous-development

一个面向 Codex / Codex++ 的通用持续开发 Skill。

它不会把项目写死成 Vue、React、Angular、Svelte、Rust、Godot、前端、后端等固定角色，而是先扫描当前仓库，再动态识别：

- 技术栈
- 项目架构
- 模块边界
- 可并行工作流
- 构建 / 测试 / Lint / 类型检查命令
- 文档约定
- Git 状态
- 可继续执行的 backlog

然后按实际项目情况动态使用子代理并行开发。

## 功能

- 动态识别任意技术栈和项目结构
- 动态决定是否需要 1～4 个子代理
- 持续开发，不因一轮任务完成就主动停止
- 支持 Typesafe AI 辅助分类 / 优先级 / 风险判断
- 自动发现项目自己的验证命令
- 更新 README / PROGRESS / TODO 等文档
- 安全 commit / push
- push 后验证本地 HEAD 是否已同步到远程
- 额度 / rate limit / 高风险操作时安全停止
- 支持定时续作与 `always()` 持续模式

## 目录

```text
continuous-development/
├── SKILL.md
├── invocation.md
├── repository.md
├── orchestration.md
├── validation.md
├── typesafe.md
├── documentation.md
├── git.md
├── quota-safety.md
├── subagents.md
├── README.md
└── LICENSE
```

`SKILL.md` 是唯一入口，其余 Markdown 是拆分后的子规则。主 Skill 会要求同步读取全部规则文件。

## 安装

### GitHub

```bash
mkdir -p ~/.codex/skills

git clone https://github.com/mhxy13867806343/continuous-development.git \
  ~/.codex/skills/continuous-development
```

### Gitee

```bash
mkdir -p ~/.codex/skills

git clone https://gitee.com/fangjiayu/continuous-development.git \
  ~/.codex/skills/continuous-development
```

## 更新

如果已经通过 Git 安装，以后本地更新只需要：

```bash
git -C ~/.codex/skills/continuous-development pull
```

如果你自己改过本地 Skill，建议先检查：

```bash
git -C ~/.codex/skills/continuous-development status
```

避免覆盖自己的本地改动。

## 使用

### 查看帮助与命令指南 (help / h)

```text
$continuous-development help
$continuous-development h
$continuous-development help()
@continuous-development help
@continuous-development h
```

查看所有支持的命令列表、详细说明及使用示例（不修改任何代码或配置）：

| 命令形式 | 模式 | 说明 |
| :--- | :--- | :--- |
| `@continuous-development help` / `h` | 帮助查询 | 打印完整命令手册与复制即用示例 |
| `@continuous-development` | 默认单次模式 | 立即开始持续开发，不改动自动化任务 |
| `@continuous-development always()` | 持续循环模式 | 任务连贯推进，不主动停止；附带每小时自动恢复机制 |
| `@continuous-development run()` | 默认定时模式 | 立即开始并开启每 1 小时定时续作任务 |
| `@continuous-development run(2h)` | 指定间隔模式 | 支持 1h/2h/3h/4h/6h/12h/24h，可附加任务目标 |
| `@continuous-development status()` | 状态查看 | 只读检查当前项目架构、Git、Backlog 及定时任务 |
| `@continuous-development stop()` | 停止定时 | 禁用当前项目的定时续作任务，不改动代码 |

### 普通持续开发

```text
$continuous-development
```

立即开始持续开发，但不主动创建或修改定时任务。

### 持续模式 + 自动恢复

```text
$continuous-development always()
```

这是推荐的“尽量不要停”模式：

- 当前会话立即开始
- 一轮结束后马上进入下一轮
- 有安全独立任务时动态使用子代理
- 不因为完成一次任务就主动停止
- 如果当前运行被平台生命周期 / 临时额度 / runtime 限制中断，则使用每小时续作任务作为恢复层

> `always()` 是 best-effort 持续运行，不代表单个 Codex 请求可以在平台上永久存活。

### 定时续作

默认每小时：

```text
$continuous-development run()
```

指定间隔：

```text
$continuous-development run(1h)
$continuous-development run(2h)
$continuous-development run(3h)
$continuous-development run(4h)
$continuous-development run(6h)
$continuous-development run(12h)
$continuous-development run(24h)
```

也可以附带当前目标：

```text
$continuous-development run(2h) 优先修复当前项目剩余 BUG
```

### 混合修饰与后值覆盖规则 (Last-Write-Wins)

支持空格分隔链式组合多个修饰符：

```text
$continuous-development always() run(0.1) xxx
$continuous-development always() run(0.1) run(1)
```

- **后值覆盖前值**：当出现多个 `run(...)` 时（例如 `run(0.1) run(1)`），后面的 `run(1)` 会自动覆盖前面的 `0.1`，最终定时间隔为 `1h`。
- **浮点/小数定时间隔**：支持小数小时，如 `run(0.1)`（约 6 分钟）、`run(0.5)`（30 分钟）等。
- **混合目标说明**：修饰符之后附带的文本（如 `xxx`）会自动作为本次开发的任务目标。

### 高级 Pythonic 组合式调用 (安全 AST 解析)

Skill 内置标准 Python AST 抽象语法树解析（纯静态语法分析，零 `eval` 安全隐患，配套工具位于 `scripts/parse_invocation.py`），支持 Python 风格的工作流编排语法：

#### 1. 下标管道切片语法
```text
$continuous-development[a, b, c(), d(1)]
```
将子代理 `a`、`b` 与参数化任务步骤 `c()`、`d(1)` 组合为批量有序流水线。

#### 2. 二元算子组装 (`+`)
```text
$continuous-development a+b+c()+d(1.2)
```
使用 `+` 操作符自由连接子代理、无参任务流与带参数工作流（如 `d(1.2)` 传参）。

#### 3. 动态可变参数 (`*args`, `**kw`)
```text
$continuous-development a+b+c()+d(1.2)+*args+**kw
```
支持在工作流末端附加可变位置参数与关键字配置，动态透传并发数、超时控制等配置。

#### 4. 函数式 / Lambda 延迟与映射执行
```text
$continuous-development lambda(run())
$continuous-development lambda(map(run()))
$continuous-development lambda(a+b+c()+d(1.2))
```
- `lambda(run())`：延迟/条件触发定时续作策略。
- `lambda(map(run()))`：跨多个任务批次映射续作调度。
- `lambda(a+b+c()+d(1.2))`：构建惰性求值的复合工作流管道。


### 查看状态

```text
$continuous-development status()
```

只检查项目、Git、backlog、验证状态和对应自动任务，不修改代码。

### 停止定时续作

```text
$continuous-development stop()
```

只关闭当前仓库对应的持续开发自动任务，不删除 Skill。

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

#### 接入验证与安全测试命令

在安装或更新后，建议在新对话中先执行只读帮助命令进行冒烟测试：

```text
@continuous-development help Sub-agent
```

- **预期行为**：仅展示子代理选择的语法、规则与示例，**绝不启动持续开发**、不扫描或修改代码、不创建定时任务。
- **注意**：能够输出帮助信息代表文档接入成功，但不代表原生环境的输入框弹窗或多代理并发已经通过实操验证。

#### 新环境自动接入提示词模版

若在其它电脑或全新环境下放置了新增规则文件，可直接复制以下提示词发送给 Codex，指导其自动完成安全局部接入：

> 请帮我接入 continuous-development 的子代理选择功能。  
> Skill 目录：`~/.codex/skills/continuous-development/`  
> 我已经把以下两个文件放进这个目录：  
> - `subagents.md`  
> - `SUBAGENTS-INTEGRATION.md`  
> 请先读取 `SUBAGENTS-INTEGRATION.md` 和 `subagents.md`，再检查当前目录里的现有文件。  
> 先备份需要修改的文件，备份放到 Skill 目录之外，然后按照接入说明，仅局部更新：  
> - `SKILL.md`  
> - `invocation.md`  
> - `orchestration.md`  
> - `README.md`  
> 要求：  
> 1. 保留现有功能和我的其他修改，不用旧版本整份覆盖。  
> 2. 在 `SKILL.md` 中接入 `subagents.md`。  
> 3. 增加 Sub-agent 的命令说明、参数解析和帮助内容。  
> 4. 先解析命令、确认子代理选择，再进入开发循环。  
> 5. `Sub-agent .` 必须等待用户选择；取消或无效输入不能默认全选。  
> 6. 没有真实选择界面能力时，使用对话编号列表，不声称已实现弹窗。  
> 7. 不把 `SUBAGENTS-INTEGRATION.md` 加入运行时规则加载列表。  
> 本次只做 Skill 文档接入，不启动持续开发，不执行 git commit/push。完成后告诉我修改了哪些内容及尚未实测的功能。

## 全局 Codex 指令

建议同时在 Codex / Codex++ 的全局“Codex 指令”中保存通用规则，例如：

- repository first
- 不猜技术栈
- 动态拆分子代理
- 保留用户已有改动
- 不提交 secrets
- 安全 commit / push
- push 后检查远程同步
- 禁止 force push / reset --hard / 生产破坏性操作

项目自己的 `AGENTS.md` 仍应优先保存项目特定规则。

## Git 安全

Skill 默认允许安全的当前分支 commit / push，但不会自动执行：

- `git push --force`
- `git push --force-with-lease`
- `git reset --hard`
- 删除远程分支
- 重写共享历史
- 删除未知用户改动
- 生产部署
- 破坏性数据库操作

这些需要用户明确确认。

## Typesafe AI

如果当前 Codex 环境已经安装 Typesafe AI，可以用于：

- task classification
- task routing
- priority ranking
- bug classification
- risk assessment
- option selection

Typesafe AI 只是辅助决策，不是持续开发的必需依赖。不可用时应继续正常开发。

## 仓库地址

- GitHub: https://github.com/mhxy13867806343/continuous-development
- Gitee: https://gitee.com/fangjiayu/continuous-development

## 本地维护与双远程同步

建议本地仓库配置两个远程：

```bash
git remote -v

git remote add github https://github.com/mhxy13867806343/continuous-development.git
git remote add gitee https://gitee.com/fangjiayu/continuous-development.git
```

如果已经有 `origin`，也可以保留 `origin`，只额外添加另一个远程。

更新后：

```bash
git add .
git commit -m "feat: update continuous-development skill"

git push github main
git push gitee main
```

## 从本地 Codex Skill 目录更新远程

如果你的工作目录就是：

```text
~/.codex/skills/continuous-development
```

那么可以：

```bash
cd ~/.codex/skills/continuous-development

git status
git add .
git commit -m "feat: update continuous-development skill"
git push github main
git push gitee main
```

之后其他电脑更新：

```bash
git -C ~/.codex/skills/continuous-development pull
```

## License

MIT
