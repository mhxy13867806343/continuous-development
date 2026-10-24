# 自动续作：watch() 方法

本版在原有完整 Skill 上新增本地后台执行程序，不只是 Markdown 规则。
**交付程序不等于已经在你的电脑上安装、启动或完成实测。**

## 最常用的方法

```text
@continuous-development watch()
@continuous-development watch("status")
@continuous-development watch("stop")
@continuous-development watch("resume")
```

开始前检查环境：

```text
@continuous-development watch("doctor")
```

显式指定参数和目标：

```text
@continuous-development watch(every="60s", retry=3, threshold=1) -- 继续当前项目已有待办
```

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `every` | `"60s"` | 本地监测/续轮间隔；运行中的轮次不会被重复启动 |
| `retry` | `3` | 已确认终止的暂时性失败最多重试几次 |
| `threshold` | `1` | 剩余额度百分比；小于等于1%暂停 |

`every` 接受带单位的整数秒/分钟/小时，范围1秒至1小时。
重试退避至少60秒，活动轮次的额度检查每60秒一次；1秒不代表每秒创建新代理。
状态和停止命令必须单独发送，不能与 always()/run()/Sub-agent 串联。
`watch()` 已存在时保留原设置，不悄悄覆盖；修改参数前应检查本地 config.json。

## 实际恢复什么

这版恢复的是**自己管理的后台 Codex 项目任务**。
它通过本地 `codex app-server` 启动专用线程，完成一轮后，根据结构化结果继续下一项。
已确认结束的临时网络失败会退避重试；额度不足时只检查恢复，不继续请求模型。

不是以下能力：
- 自动点击当前 GUI 聊天里的继续按钮，或接管所有现有20个会话；
- 重启 npm/Godot/后端开发服务；
- 同时控制 Claude Code、Antigravity、Kiro；
- 在无法确定旧任务是否还运行时，强行重开；
- 在你主动停止、等待批准、任务完成时继续烧额度。

### 防止重复改代码

默认创建**独立 Git 工作树和本地 `cd-watch/...` 分支**，不直接写原工作目录。
第一轮从已提交的 HEAD 开始。原目录有未提交修改时先报出阻塞，不替你stash、reset或提交。
`watch("status")` 的 `config.workspace` 是后台修改所在目录；`config.branch` 是分支。
成果不会自动合并回当前分支，也不会自动推送远程。必须检查差异并按项目流程整合。

此版后台执行保持单个主代理，禁止脱离轮次的子代理/命令。正常会话里的 Sub-agent 功能保留。
这是一版有限、可检查的执行器，不是对原有所有客户端自动化功能的完成声明。

## 安装包怎么放

先备份原 Skill。将整个 `continuous-development` 目录内文件合并到：

```text
~/.codex/skills/continuous-development/
```

保留原 `.git` 和个人修改。不要多套一层同名目录，不要替换全局 AGENTS.md/config.toml。
本包已接入 watch 路由，不需要执行旧的增量安装器。
在 Codex 可识别该 Skill、且具有终端和本地服务权限的对话中使用方法。
如果是 `$` 提及界面，将 `@continuous-development` 换为 `$continuous-development`。

复制文件本身不会创建服务；首次明确调用 watch() 时，Skill 才应执行实际安装脚本。

## 环境要求

macOS + Python 3.9以上 + Git + `codex` 可执行文件 + ChatGPT方式登录。
原生LaunchAgent写入：`~/Library/LaunchAgents/local.continuous-development.watch.<hash>.plist`。
任务状态和独立工作树：`~/.codex/continuous-development/watch/<hash>/`，或对应 CODEX_HOME 目录。

当前任务没权限操作后台服务时应报告缺少权限，不自动调整系统安全设置。
没有 CLI 或不是 ChatGPT登录时不启动，不自动切换付费API。
本地进程重启不能保证模型不会扣除已有credits，请自行核对账户的额外付费设置。

## 脚本备用入口

这些是给Skill调用的实际脚本；通常只需上面的聊天方法。

```bash
# 环境检查，不启动模型轮次
python3 ~/.codex/skills/continuous-development/scripts/watch_runtime.py \
  --project /你的项目路径 --invocation 'watch("doctor")'

# 预览，不安装服务
python3 ~/.codex/skills/continuous-development/scripts/watch_runtime.py \
  --project /你的项目路径 --invocation 'watch()'

# 明确启用macOS后台服务
python3 ~/.codex/skills/continuous-development/scripts/watch_runtime.py \
  --project /你的项目路径 --invocation 'watch() -- 继续已有待办' --apply

# 停用，不删除代码/分支/交接记录
python3 ~/.codex/skills/continuous-development/scripts/watch_runtime.py \
  --project /你的项目路径 --invocation 'watch("stop")' --apply
```

## 怎样看才算开启成功

分开检查：`service.registered`、`enabled`、`worker_lock_held`、`state.phase`。
`service_registered` 只表示服务登记成功；如果 phase 是 connecting/quota_wait/needs_user，
就不能说正在开发。`execution:not_executed` 仅是命令解析或预览。
停止后若 `stop_requested=true` 但锁仍被占用，表示正在等安全中断，并非已停止。

## 验证范围

新旧共124项测试在打包环境通过。新增部分覆盖真实临时Git工作树、进程锁、参数解析、
额度政策及假App Server子进程的握手、事件、恢复、批准拒绝、停止与错误处理。
假服务没有请求真实模型。没有在你的macOS、真实Codex版本、账户和LaunchAgent上运行实测。

## 已核对的接口资料

- Codex App Server: https://developers.openai.com/codex/app-server/
- Developer commands: https://developers.openai.com/codex/cli/reference/
- Codex platform integration: https://developers.openai.com/blog/codex-as-a-platform

具体安装版本返回不兼容协议时，本程序暂停并报告，不用假状态继续执行。

- macOS LaunchAgents: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
