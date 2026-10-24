# continuous-development 命令与方法示例大全 (Examples & Cheatsheet)

本文件汇总了 `continuous-development` Skill 支持的所有调用方法、组合语法、生命周期控制及实际调用示例。

前缀说明：支持 `@continuous-development` 或 `$continuous-development`（在支持 `$` 的宿主中），二者等价。

---

## 目录

1. [基础开发与只读帮助](#1-基础开发与只读帮助)
2. [持续循环与定时续作 (always / run)](#2-持续循环与定时续作-always--run)
3. [子代理选择与调度 (Sub-agent)](#3-子代理选择与调度-sub-agent)
4. [Pythonic 管道与 AST 组合表达式](#4-pythonic-管道与-ast-组合表达式)
5. [会话生命周期与交接 (sessions / handoff / open)](#5-会话生命周期与交接-sessions--handoff--open)
6. [低额度保护与定时同步 (sync)](#6-低额度保护与定时同步-sync)
7. [真实后台守护与自动续作 (watch)](#7-真实后台守护与自动续作-watch)
8. [CLI 调试与解析自测 (Scripts)](#8-cli-调试与解析自测-scripts)
9. [完整速查表 (Cheat Sheet)](#9-完整速查表-cheat-sheet)

---

## 1. 基础开发与只读帮助

### 1.1 默认即刻开发
启动一次常规的持续开发循环。不改动任何定时器或自动化配置。
```text
@continuous-development
$continuous-development
```
带具体目标：
```text
@continuous-development 完善用户鉴权模块并补充单元测试
```

### 1.2 完整帮助信息 (只读)
打印全部命令与参数说明，不修改代码，不触发 Git 提交或自动化。
```text
@continuous-development help
@continuous-development h
@continuous-development help()
$continuous-development help
```

### 1.3 状态检查 (只读)
探测当前仓库技术栈、架构、Git 差异、分支同步状态与待办项，不进行任何修改。
```text
@continuous-development status()
@continuous-development status
$continuous-development status()
```

### 1.4 停止自动化
关闭为当前仓库创建的持续开发定时任务（不删除任务，不修改源代码）。
```text
@continuous-development stop()
@continuous-development stop
$continuous-development stop()
```

---

## 2. 持续循环与定时续作 (always / run)

### 2.1 不停机持久循环 `always()`
进入持续编排模式，当轮次完成后立即寻找下一个任务，不主动停机；同时确保存在每小时恢复定时器作为保底兜底。
```text
@continuous-development always()
$continuous-development always()
```
带具体开发目标：
```text
@continuous-development always() -- 重构支付模块并补全端到端测试
```

### 2.2 定时续作 `run(<interval>)`
立即开始开发，并创建/复用对应周期的后台定时任务。支持小数小时与常用小时单位。
```text
# 每 6 分钟 (~0.1h) 触发一次
@continuous-development run(0.1)

# 每 30 分钟 (~0.5h) 触发一次
@continuous-development run(0.5)

# 每 1 小时（默认值）
@continuous-development run()
@continuous-development run(1h)

# 每 2 小时 / 6 小时
@continuous-development run(2h)
@continuous-development run(6h) continue the current priority backlog
```

### 2.3 链式组合与覆盖规则 (Last-Write-Wins)
可以在一条命令中组合修饰符，靠右侧（后出现）的参数覆盖前面的参数：
```text
# always() 开启持久模式，run(0.1) 配置约 6 分钟保底间隔，附带目标 "fix-auth"
$continuous-development always() run(0.1) fix-auth

# 后面的 run(1) 会覆盖前面的 run(0.1)，最终为 1 小时间隔
$continuous-development always() run(0.1) run(1)
```

---

## 3. 子代理选择与调度 (Sub-agent)

### 3.1 子代理专用帮助 (只读)
只展示子代理选择语法、规则与示例，作为安全的只读自检命令：
```text
@continuous-development help Sub-agent
@continuous-development h Sub-agent
@continuous-development help() Sub-agent
```

### 3.2 子代理选择语法
从当前环境可用的 Agents 名单中选择参与任务的子代理：

* **全选当前可用子代理**：
  ```text
  @continuous-development Sub-agent
  @continuous-development Sub-agent()
  ```
* **选择单个子代理**：
  ```text
  @continuous-development Sub-agent(tester)
  ```
* **选择多个子代理**：
  ```text
  @continuous-development Sub-agent(frontend, backend, reviewer)
  @continuous-development Sub-agent([frontend, backend, reviewer])
  @continuous-development Sub-agent frontend, backend, reviewer
  ```
* **请求交互式弹窗选择**（由用户在界面中勾选）：
  ```text
  @continuous-development Sub-agent .
  @continuous-development Sub-agent(.)
  ```

### 3.3 模式与子代理组合
将执行模式放在前，子代理在后，目标使用 `--` 分隔：
```text
@continuous-development always() Sub-agent(tester, linter) -- 持续跑测并修复 lint
@continuous-development run(2h) Sub-agent(frontend) -- 完成订单页重构
@continuous-development status() Sub-agent
```

---

## 4. Pythonic 管道与 AST 组合表达式

支持经由 AST 安全解析的 Python 表达式（无 `eval()` 风险），用于灵活表达工作流管线。

### 4.1 下标管道语法 (`[]`)
```text
# 选择 agent a, b，并串联调用 c() 与带参步骤 d(1)
$continuous-development[a, b, c(), d(1)]
```

### 4.2 加法组合语法 (`+`)
使用 `+` 操作符串联多个阶段或并发代理：
```text
$continuous-development a + b + c() + d(1.2)
```

### 4.3 动态参数转发 (`*args`, `**kw`)
向编排器传递位置参数与关键字参数：
```text
$continuous-development a + b + c() + d(1.2) + *args + **kw
```

### 4.4 延迟求值与批量映射 (`lambda(...)`)
用于定义延迟执行或按批次映射的流程：
```text
# 延迟执行的 run 计划
$continuous-development lambda(run())

# 针对待办列表映射执行
$continuous-development lambda(map(run()))

# 延迟组合工作流
$continuous-development lambda(a + b + c() + d(1.2))
```

---

## 5. 会话生命周期与交接 (sessions / handoff / open)

生命周期管理命令优先独立路由，一条消息仅限一个管理命令，不会自动落入通用循环。

### 5.1 会话批量与轮数管理 `sessions(...)`
接管一批已验证的初始会话，轮转归档老会话，并在数量上限内补充新会话：
```text
# 接管最多 20 个初始会话，并发上限 15，单个会话阈值 15 轮
@continuous-development sessions(initial=20, limit=15, rounds=15)

# 指定作用域为 host
@continuous-development sessions(initial=20, limit=15, rounds=15, scope="host")

# 查看当前会话管理器状态 (只读)
@continuous-development sessions("status")

# 停止会话管理器
@continuous-development sessions("stop")
```

### 5.2 状态交接导出 `handoff(...)`
安全导出结构化 Markdown 交接文档，记录来源 ID、代码状态与接续点（不泄露敏感凭证）：
```text
# 导出当前会话的交接记录
@continuous-development handoff()

# 针对指定会话 ID 或 URL 导出交接
@continuous-development handoff("session-xyz-123")
@continuous-development handoff("https://codex.local/threads/thread_abc")
```

### 5.3 项目与线程进度查看 `open(...)` (只读)
查询指定项目或线程的真实落地进度，返回只读事实：
```text
# 查看当前项目进度
@continuous-development open()

# 查看指定项目或线程的进度
@continuous-development open("continuous-development")
@continuous-development open("https://codex.local/threads/thread_abc")
```

---

## 6. 低额度保护与定时同步 (sync)

### 6.1 周期同步与额度熔断 `sync(...)`
配置自动化同步计划与低额度安全停机门禁：
```text
# 每 5 分钟同步一次，当额度 <= 1 时触发 "保存检查点-推送Git-暂停"
@continuous-development sync(every="5m", threshold=1, on_low="checkpoint-push-pause")

# 每 10 分钟同步，额度阈值设为 2
@continuous-development sync(every="10m", threshold=2, on_low="checkpoint-push-pause")

# 查询同步任务状态 (只读)
@continuous-development sync("status")

# 停用同步任务
@continuous-development sync("stop")
```

---

## 7. 真实后台守护与自动续作 (watch)

`watch()` 是本地后台执行器（macOS LaunchAgent + Codex App Server），在独立 Git Worktree 与独立线程中运行，具备严格单轮约束与防跑飞熔断。

### 7.1 启动与配置 `watch(...)`
```text
# 以默认参数（每 60 秒检查，最多重试 3 次，额度阈值 1）启动
@continuous-development watch()

# 显式指定参数
@continuous-development watch(every="60s", retry=3, threshold=1)

# 带具体目标任务的启动
@continuous-development watch(every="30s", retry=5, threshold=2) -- fix existing test failures
```

### 7.2 诊断与健康检查 `watch("doctor")` (只读)
检查当前项目的 Git 状态、Codex 二进制位置、ChatGPT 授权及模型额度，不消耗模型 Token：
```text
@continuous-development watch("doctor")
```

### 7.3 状态回读 `watch("status")` (只读)
读取当前守护进程的真实系统状态（服务注册状态、锁持有、当前阶段 Phase、最后检查点）：
```text
@continuous-development watch("status")
```

### 7.4 优雅停止与手动恢复
```text
# 请求优雅中断当前轮次并解绑 LaunchAgent 守护服务
@continuous-development watch("stop")

# 在人工修复/审核阻塞原因后，手动恢复已停止的任务
@continuous-development watch("resume")

# watch 专属帮助说明 (只读)
@continuous-development help watch
```

---

## 8. CLI 调试与解析自测 (Scripts)

开发者或 CI 流程可在本地直接调用脚本进行零副作用验证：

### 8.1 语法解析器安全自检 (`parse_invocation.py`)
仅解析意图，返回 JSON 结构树，不产生任何副作用：
```bash
# 解析生命周期命令
python3 scripts/parse_invocation.py '@continuous-development sessions(initial=20, limit=15, rounds=15)'

# 解析 watch 命令
python3 scripts/parse_invocation.py '@continuous-development watch(every="30s", retry=2)'

# 解析复合 AST 语法
python3 scripts/parse_invocation.py '$continuous-development[a, b, c(), d(1)]'
```

### 8.2 Watch 运行时命令行 (`watch_runtime.py`)
```bash
# 只读状态查询 (不带 --apply)
python3 scripts/watch_runtime.py --project . --invocation 'watch("status")'

# Doctor 诊断
python3 scripts/watch_runtime.py --project . --invocation 'watch("doctor")'

# 真实注册并启动本地服务 (带 --apply)
python3 scripts/watch_runtime.py --project . --invocation '@continuous-development watch()' --apply

# 真实注销并停止服务
python3 scripts/watch_runtime.py --project . --invocation 'watch("stop")' --apply
```

---

## 9. 完整速查表 (Cheat Sheet)

| 功能类别 | 典型命令示例 | 性质 | 核心作用与说明 |
| :--- | :--- | :---: | :--- |
| **常规开发** | `@continuous-development` | 写入 | 立即启动单次持续开发循环 |
| **只读帮助** | `@continuous-development help` | 只读 | 打印所有命令语法与使用范例 |
| **状态查询** | `@continuous-development status()` | 只读 | 检查代码库架构、Git 差异与待办项 |
| **停止计划** | `@continuous-development stop()` | 配置 | 禁用当前仓库的定时自动化任务 |
| **不停机循环** | `@continuous-development always()` | 持续 | 保持编排器持续工作，辅以每小时恢复机制 |
| **定时调度** | `@continuous-development run(0.5)` | 调度 | 每 30 分钟 (~0.5h) 自动唤醒续作一次 |
| **子代理全选** | `@continuous-development Sub-agent()` | 调度 | 选派全部可用 Sub-agent 参与协作 |
| **子代理指定** | `@continuous-development Sub-agent(a, b)` | 调度 | 选派指定的 a 和 b 代理 |
| **子代理弹窗** | `@continuous-development Sub-agent .` | 交互 | 请求在 UI 界面交互式勾选代理名单 |
| **子代理帮助** | `@continuous-development help Sub-agent` | 只读 | 仅输出 Sub-agent 选择语法与规范 |
| **管道下标** | `$continuous-development[a, b, c()]` | 组合 | 管道化顺序编排多代理与步骤 |
| **算子串联** | `$continuous-development a + b + c()` | 组合 | 基于 Python 加法表达式连接各环节 |
| **延迟执行** | `$continuous-development lambda(run())` | 调度 | 延迟或条件化执行定时任务 |
| **会话管理** | `sessions(initial=20, limit=15)` | 管理 | 控制并发会话总数与生命周期轮换 |
| **会话状态** | `sessions("status")` | 只读 | 查看当前会话管理器的活跃指标 |
| **交接导出** | `handoff()` | 导出 | 导出安全结构化的 Markdown 交接上下文 |
| **进度查看** | `open()` | 只读 | 读取并计算仓库已验证落地的真实进度 |
| **额度同步** | `sync(every="5m", threshold=1)` | 同步 | 定期同步并在额度低于阈值时推送暂停 |
| **同步状态** | `sync("status")` | 只读 | 查看当前后台同步作业运行状态 |
| **后台守护** | `watch()` | 本地后台 | 在独立工作树与守护服务中无人值守续作 |
| **环境诊断** | `watch("doctor")` | 只读 | 检测 Git/Codex/额度状态，不耗费 Token |
| **守护状态** | `watch("status")` | 只读 | 回读 LaunchAgent 真实运行阶段与锁状态 |
| **守护中断** | `watch("stop")` | 本地后台 | 优雅中断守护任务并卸载本地服务 |
| **守护恢复** | `watch("resume")` | 本地后台 | 在人工确认后恢复已阻塞或停止的守护任务 |
