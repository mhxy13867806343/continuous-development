# watch() 完整更新包

本文件其余部分保留上一版安装说明。此次新增 watch.md、README-WATCH.md、
scripts/watch_policy.py、watch_rpc.py、watch_runtime.py，并已接入 SKILL.md 和解析器。
直接合并整个目录，保留 .git 与个人修改；不要运行旧的增量安装器。

**watch() 有实际 macOS/Codex 后台执行脚本，但未在你的电脑安装或实测。**
它使用独立工作树和专用线程；旧版 sessions/sync 等模块仍未接通完整执行器。
使用方式、限制与测试范围见 [README-WATCH.md](README-WATCH.md)。

---

# 完整目录包：安装与使用

这是已经合并的 continuous-development 完整目录，不是单独的增量扩展包。
原有规则、Sub-agent 文档、命令解析脚本，以及新增 sessions / handoff / open / sync
规则与策略脚本已经放在同一个目录中；主入口与解析器接入已经完成。

## 直接放到你原来使用的目录

目标：`~/.codex/skills/continuous-development/`

1. 在下载目录解压 ZIP，得到一个 `continuous-development` 文件夹。
2. 先把现有 Skill 目录完整备份到技能目录之外，例如桌面或其他备份目录。
3. 将解压后文件夹内的文件与子目录合并到现有 `continuous-development` 目录。
4. 同名文件是本完整包的接入版本；已有自己的修改时先比对合并，不要直接覆盖自定义内容。
5. 保留旧目录内的隐藏 `.git`（存在时），本压缩包不包含也不会替换 `.git`。
6. 最终应该能直接找到 `continuous-development/SKILL.md`，不要多套一层同名文件夹。

本包已经接入完毕，不需要再执行 `install_extension.py --apply`。
`install_extension.py` 和接入文档仍保留，供维护者将相同扩展合并到其他旧副本时使用。

## 不要做这些操作

不要删除旧目录后丢掉原来的 `.git` 或个人修改。
不要把整个 ZIP 留在 Skill 目录里作为安装；需要先解压。
不要把备份目录也放在同一个 Skill 扫描目录中形成重复入口。
不要把 `~/.codex/AGENTS.md` 或 `config.toml` 替换成本包文件。

## 首次检查

在实际能识别该 Skill 的界面新建会话，先用只读命令检查规则加载：

```text
@continuous-development help
```

或在使用 `$` 前缀的界面：

```text
$continuous-development help
```

Python 解析自检（只打印 JSON，不管理真实会话、不连接远程）：

```bash
python3 ~/.codex/skills/continuous-development/scripts/parse_invocation.py \
  '@continuous-development open()'
```

输出中的 `execution: not_executed` 表示只解析了意图，不是已经完成进度查询。

## 新增工作流命令

```text
@continuous-development sessions(initial=20, limit=15, rounds=15)
@continuous-development sessions("status")
@continuous-development sessions("stop")
@continuous-development handoff()
@continuous-development open()
@continuous-development open("项目名称或ID")
@continuous-development sync(every="5m", threshold=1, on_low="checkpoint-push-pause")
@continuous-development sync("status")
@continuous-development sync("stop")
```

一个消息只使用一个新增管理命令。它们不会自动落入普通开发循环。

## 完整目录不等于完整客户端实现

本包交付了规则、配置样例、模板、安全解析及策略计算，未附带已经接通所有客户端的
会话控制器、真实额度接口、后台定时器或自动 Git 推送执行器。

因此，复制文件不会自动接管20个聊天、弹出原生选择框、归档/新建会话或每5分钟推送。
真实动作需当前宿主有相应工具，并以实际操作与回读验证结果为准。
未具备能力时必须说明未执行，不能只凭命令被识别就声称已启用。

## Git 更新提醒

这个 ZIP 不是 Git 克隆，也没有创建任何 Git 提交。合并到已有克隆目录后，
本地文件会表现为未提交的修改；后续 `git pull` 前先用 `git status` 检查并保留这些改动。
不要使用 `reset --hard` 或删除 `.git` 来绕过冲突。本次没有提交或推送任何仓库。

## 文件索引

- `SKILL.md`：主入口，包含全部运行规则引用。
- `subagents.md`：子代理选择规则；`orchestration.md`：已选名单内的调度。
- `session-lifecycle.md`：首批处理、轮数阈值、归档换新与数量上限。
- `handoff.md`：来源ID、链接和私有交接。
- `progress.md`：只读进度查询与真实进度计算依据。
- `sync-quota.md`：同步与低额度保护规则。
- `host-adapters.md`：宿主能力边界。
- `lifecycle.defaults.json`：配置样例；解析器的默认值以 scripts/lifecycle_policy.py 为准。
- `README-SESSION-MANAGEMENT.md`：新增命令详细说明。
- `IMPLEMENTATION-STATUS.md`：已完成范围和未接通的实际能力。
- `docs/TEST-RESULTS.txt`：本包重新执行的单元测试结果。
