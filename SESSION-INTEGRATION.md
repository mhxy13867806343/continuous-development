# 会话管理扩展：接入顺序与运行验收

> 完整目录包说明：本包已经按下列接入规则合并完成，不必再次手动接入或运行增量安装。下文的接入步骤供更新其他旧副本时参考；实际客户端能力仍需单独接通与验证。

## 交付边界

本包是增量规则 + 可执行的**解析/策略计算**，不是生产会话控制器。`scripts/lifecycle_policy.py` 不归档、不建会话、不创建定时、不执行 Git。它的输出固定带 `execution: not_executed`。

当前仓库已有 `scripts/parse_invocation.py`。读取版本 blob SHA：`bcf532c59b9875de432e212b95ad02843e279a09`。其中 AST 处理中没有保留 keyword arguments，而且旧 h/help 正则可能匹配新命令中的字母。因此新命令应在旧逻辑之前独立解析；不能仅新增 Markdown 然后直接宣称命令可运行。

以下是接入说明，不是已经修改了远程仓库的记录。

## 快速本地接入

本包提供 `install_extension.py`，将下面规定的局部补充自动合并到现有文件。
解压后先运行 dry-run，再按需 `--apply`；脚本没有 Git 提交/推送或宿主操作。

```bash
python3 install_extension.py --target "$HOME/.codex/skills/continuous-development"
python3 install_extension.py --target "$HOME/.codex/skills/continuous-development" --apply
```

默认备份位置：`~/.continuous-development/backups/<时间-随机ID>/`，不在技能扫描目录内。
遇到已修改的同名扩展文件或原入口结构变化时停止，保留用户文件，按下列步骤手动合并。

## 一、文件

新增：

```text
session-lifecycle.md
handoff.md
progress.md
sync-quota.md
host-adapters.md
lifecycle.defaults.json
templates/SESSION-HANDOFF.md
scripts/lifecycle_policy.py
tests/test_lifecycle_policy.py
README-SESSION-MANAGEMENT.md
SESSION-INTEGRATION.md
docs/SOURCES.md
```

局部修改现有：SKILL.md、invocation.md、orchestration.md、quota-safety.md、git.md、documentation.md、README.md、scripts/parse_invocation.py。保留 subagents.md 及原有功能，不能用旧整仓覆盖。

保持当前已经生效的安装目录，例如 `~/.codex/skills/continuous-development/`。备份放到 Skill 目录外。

## 二、入口规则

在 SKILL.md 原规则加载列表增加以下五项：

```markdown
10. `session-lifecycle.md`
11. `handoff.md`
12. `progress.md`
13. `sync-quota.md`
14. `host-adapters.md`
```

在 `## Command routing takes precedence` 中、通用开发行为之前追加：

```markdown
For sessions(), handoff(), open(), and sync(), parse the lifecycle command
before entering any generic development, Git, or automation workflow.
Follow session-lifecycle.md, handoff.md, progress.md, sync-quota.md and
host-adapters.md. These commands are distinct from subagent selectors.
open() and the lifecycle "status" actions are read-only and return after
reporting. handoff() exports a local handoff only; it does not independently
archive a session or start development. Lifecycle stop actions only disable
their own manager/job and must not fall through to the development loop.

A parser result or a saved policy document is not execution evidence.
Never claim sessions are archived/created or a timer is enabled unless the
real host operation succeeded and was re-observed. If unsupported, report
that fact and preserve safe local progress; do not fabricate success.

The round threshold, thread cap, initial drain, quota gate, unresolved
approval, pending selection, or explicit user restriction takes precedence
over generic always()/do-not-stop instructions.
```

不要把本接入说明、SOURCES、测试和模板全部加入每次运行加载列表。

## 三、命令路由

在 invocation.md 增加：

```markdown
### Lifecycle management

- sessions(initial=20, limit=15, rounds=15, scope="host"): adopt an observed
  initial batch, drain existing work, archive verified finished sessions,
  then create successors within the configured cap. See session-lifecycle.md.
- sessions("status") / sessions("stop"): inspect or disable this manager.
- handoff([target]): save a private Markdown handoff and actual source identity.
- open([target]): read-only project/thread progress; never guesses current ID.
- sync(every="5m", threshold=1, on_low="checkpoint-push-pause", remotes=[...]):
  request a verified local/host Git synchronization schedule and low-quota gate.
- sync("status") / sync("stop"): inspect or disable that sync schedule.

Square brackets above mean optional argument, not mandatory list syntax.
Use quoted values for paths, names with spaces, IDs or URLs with punctuation.
Only one lifecycle command per message is accepted in this extension.
Existing always/run/Sub-agent composition remains unchanged. Never pass the
new lifecycle names through the legacy generic-agent/call fallback.
```

新 sync 的 5m 是同步检查周期，不改变旧 run(...) 的含义。旧 run 解析可以接受一个数值，也不证明宿主真支持该频率。

## 四、解析器接入

先运行本包测试，然后在现有 `scripts/parse_invocation.py` 接入新解析器。不要重写旧 parser 的其他行为。

模块顶层增加同目录导入（若将 scripts 作为 package 导入，采用项目现有的相对导入方式）：

```python
from lifecycle_policy import parse_lifecycle
```

在现有 `InvocationParser.parse(self, raw_input)` 的**第一处解析操作之前**增加：

```python
lifecycle = parse_lifecycle(raw_input)
if lifecycle is not None:
    return lifecycle
```

注意：新命令语法错误会抛出 ValueError。调用层必须返回明确错误并停止，不得捕获后继续进入旧“默认开发”逻辑。CLI 可以输出 JSON error 并 exit 2；技能工具层应返回无副作用错误。

返回值采用独立 schema `continuous-development.lifecycle-intent.v1`，执行分发器按 schema/command/action 处理；不要把这个对象当旧 parser 的 pipeline。旧命令返回 None 才交回旧解析器。

本版故意不支持把 sessions() 或 sync() 嵌入 lambda/map/任意 Python 表达式，不执行 eval/exec，不允许 **kwargs 展开。防止管理操作被藏在不透明表达式里。

## 五、流程规则的局部优先级

在 orchestration.md 循环派发之前加入：

```markdown
Apply enabled lifecycle and quota admission checks before dispatching work.
A thread with rotation_requested must finish only its current scoped task.
A completed assistant turn alone is not business-task completion.
Respect initial drain and atomically reserved thread capacity. Never use
subagents or hourly recovery to evade a paused controller or a quota gate.
Only a verified completed task with a saved handoff and safe execution state
may enter the archive/create transaction.
```

在 quota-safety.md 追加：

```markdown
When sync-quota protection is enabled, an authoritative remaining allowance
at or below its configured threshold is a valid protective pause even if the
platform has not yet rejected requests. This takes precedence over the old
"stop only on actual limit errors" rule. Unknown/stale allowance must not be
reported as a numeric value. Persist checkpoints throughout work because a
hard limit can prevent a final model-generated summary.
```

在 git.md 追加：

```markdown
A periodic sync tick may publish only authorized reviewed checkpoints,
never arbitrary dirty work. Use per-repository locks and explicit destinations.
Verify each remote independently against the actual pushed commit. A public
Skill repository is not a destination for unrelated project code or private
conversation handoffs. Retry failures without force-push or empty commits.
```

在 documentation.md 追加：

```markdown
Maintain private host/thread handoffs separately from public project progress.
open() percentages describe only a known task-snapshot denominator. Use unknown
when evidence is missing. Record actual archive/create/sync receipts, not plans
as completed operations. Avoid committing a document merely to insert the SHA
of the commit containing that same document: record sync receipts in local state.
```

README.md 引用 README-SESSION-MANAGEMENT.md，并在帮助列表中增加新命令，明确它们的宿主依赖。

## 六、控制器与适配器：需要在用户机器完成的接入

1. 只读识别当前宿主、版本、账户、项目与可用工具，建立 capability report。
2. 实现真实 session list/read/execution-state/archive/create，验证非归档主会话统计与分页完整性。
3. 建立本地私有 state、原子保存、scope 锁、事务 ID、创建槽位预留和崩溃恢复日志。
4. 将 admission_budget、rollover_decision、quota_decision 的计算用于实际控制器；这些函数本身不提供锁或执行能力。
5. 将项目任务清单映射到 progress_summary，完成状态需验证。
6. 实现单次安全 sync tick，并先用临时本地 bare Git 仓库测试；不得一上来推真实项目。
7. 用户允许后安装真实 300 秒调度器，读取安装状态并执行一次安全 smoke test。
8. 四个宿主分别验收；未实现的适配器必须标为 unsupported，不能假装共用 Codex 的 API。

缺少其中能力时输出对应缺口；不要直接修改客户端内部数据库、绕过权限、伪造运行结果。

## 七、验证

### 本包已可运行的单元测试

```bash
python3 -m unittest discover -s tests -p 'test_lifecycle_policy.py' -v
```

覆盖字面量参数、未知参数/恶意表达式拒绝、20→15 收敛、14余1、归档10补10、预留并发计数、首批清空屏障、轮数与任务完成区别、未知额度、usedPercent 转换、恢复防抖、进度分母。

这些是**纯函数测试**，不是跨应用真实归档/新建、原子锁、Git 上传或5分钟运行的验收。

### 必须在安装环境实测

| 场景 | 正确结果 |
| --- | --- |
| 手头实际21个，但 initial=20 | 实际接管名单20；剩余1不修改但按范围占容量 |
| 20个旧会话正在运行 | 不强杀，不新增，逐项安全完成 |
| 达到15轮但任务未完成 | drain_current_task，继续当前任务，不派新任务 |
| 主线程结束但子代理还工作 | 等待，不归档联动删除/终止子代理 |
| 归档接口失败 | 不释放槽位，不新建，不标完成 |
| 新建请求超时但其实已成功 | 查询对账，一次事务最多一个后继 |
| 两个线程竞争最后一个名额 | 原子锁保证只一个创建成功 |
| 人工新增导致16个 | 本控制器不新增，不乱归档人工会话 |
| open()没有当前身份 | 报unknown，不猜最新聊天 |
| 两个同名项目 | 列候选，不改代码 |
| 比例来源是已使用99% | 剩余1%，触发保护 |
| 额度源断开或数据过期 | unknown，暂停新派发，不报精确百分比 |
| 上传时文件还在被代理修改 | 跳过本次，不把半成品提交 |
| GitHub成功/Gitee失败 | 分别报告，只重试失败项 |
| 没有安全提交 | 无空提交，仅本地保存 |
| 到低额度但新旧聊天接口不可用 | 保存/暂停，不假归档，不创建新聊天烧额度 |
| Mac休眠15分钟 | 恢复一次对账，不承诺准点、不连续补发模型任务 |
| 只有文档，没有控制器 | 明确 not_enabled/unsupported |

## 八、发给 Codex 的接入指令

```text
按 SESSION-INTEGRATION.md 将这份会话管理扩展接入当前 continuous-development。
先备份，再局部修改原文件，不覆盖原有 Sub-agent/help/run/always 功能。
先跑新增单元测试，再接入 parse_invocation.py 的前置路由，错误不能落入开发循环。
本次先完成文档、解析和策略接入；实际会话适配器/本地定时器先只读探测。
只有真实接口可用并通过验收，才报告对应能力可执行。
没有接口时输出缺口，不直接写客户端内部数据库，不用删除冒充归档。
不 commit、不 push、不创建 PR；不把用户业务代码或完整聊天写进这个公开 Skill 仓库。
不要声称已经处理了我的现有20个会话或已经启用了5分钟同步。
```
