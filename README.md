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
