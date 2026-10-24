# 资料与版本依据

核对日期：2026-10-24。本文区分仓库已有内容、官方能力与本包设计，不将后者冒充官方原生命令。

## 仓库当前读取

- GitHub：`mhxy13867806343/continuous-development`，默认分支读取。
- SKILL.md blob：`1b1f8178cff09de9177dc4d41070c6a042f849a1`。
- invocation.md blob：`4aad22b04c35bb80b9de7462d3eecdcac04d6484`。
- scripts/parse_invocation.py blob：`bcf532c59b9875de432e212b95ad02843e279a09`。
- 已有子代理选择、组合命令和 AST 参数解析；本包只扩展新的管理命令，不回退这些已有内容。
- Gitee 访问未成功，不能据此断言其为空或已经镜像同步。

这些是读取到的文件内容 SHA，不是本包新建的 commit SHA，也不是用户本地安装版本的证明。

## 官方能力参考

### OpenAI

- https://developers.openai.com/codex/app-server/ （当前跳转到 https://learn.chatgpt.com/docs/app-server ）
  - 参考 thread/start、thread/list、thread/read、thread/archive、account/rateLimits/read。
  - usedPercent 表示已用比例，不能直接当作剩余比例。
  - 归档会尝试处理派生后代线程，需要额外检查运行安全。
- https://developers.openai.com/plugins/build/skills
  - Skill 提供工作流规则；实际数据和动作需要工具实现。
- https://developers.openai.com/codex/app/automations/
  - 宿主计划任务的运行环境与限制应实机核实，不把本聊天工具的频率限制推广到所有调度器。
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-personal-plans
  - 用量/credits 由账户规则管理；本包提示词不能充当硬计费开关。

### Claude Code

- https://code.claude.com/docs/en/sessions
  - 官方会话管理、恢复和分支参考；未据此承诺任意外部 Skill 都有 Desktop 批量归档权限。

### Antigravity

- https://www.antigravity.google/docs/cli/conversations/
  - CLI 工作目录范围、恢复和 fork 参考；不将 CLI 能力等同于 IDE 界面自动管理能力。

### Kiro

- https://kiro.dev/docs/cli/chat/session-management/
  - 会话 ID、恢复、列举和新会话参考；导出会话包或删除不是 UI 归档。

### Apple

- https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
  - “Running a Job Periodically” 给出 StartInterval=300 的五分钟示例。

## 本包自主设计

`sessions()/handoff()/open()/sync()` 名称、默认20/15/15、剩余额度阈值1%、防抖、首批先清空、容量预留、交接模板和只读策略脚本均为本包的设计约定，不是这些软件通用的内建功能。

未在用户机器验证：会话接口授权、具体客户端版本兼容、跨应用控制器、真实归档/新建、额度数据可见性、调度器安装、真实 GitHub/Gitee 上传。
