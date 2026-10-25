# JS 箭头函数快捷命令与提示

## 交付范围
本扩展给现有 continuous-development 增加：JS 箭头函数静态解析、命令别名、参数默认值、顺序展开、只读命令提示、参数提示以及客户端可调用的补全 JSON 接口。

**没有给原生 Codex/Codex++ 输入框安装实时弹窗插件。** 发送 `a` 后得到候选与“未发送时就弹菜单”是两种能力；后者还需要客户端开发者接入本地补全接口。不要把解析成功、规则生效和 GUI 已集成混为一谈。

扩展不自动执行用户 JS，不包含任意 JavaScript 运行器。真正的开发和 watch 等动作仍由 Codex 使用既有规则和工具执行。

## 三种箭头写法
复制 `commands/shortcuts.example.js` 为同目录 `shortcuts.js` 即可自定义。不存在自定义文件时使用内置示例：

```javascript
// 多参数 + 代码块
const a = (b, c) => {
  task(b);
  task(c);
};

// 零参数
const b = () => {
  status();
};

// 单参数，省略括号
const c = project => {
  open(project);
};

// 默认参数 + 对象选项
const auto = (every = "60s", threshold = 1) => {
  watch({every, retry: 3, threshold});
};
```

用户原来写的 `const b=c=>{...}` 同样支持；这里为了避免和上面的零参数 `b` 同名，示例改成 `c`。同一份文件不能重复声明相同 const 名称。

`xxx` 和 `...` 是占位符，不是可执行命令。把业务描述写进 `task("需要做的事情")`。

也支持表达式函数体：

```javascript
const check = () => watch("doctor");
const repair = target => task(`修复 ${target} 并添加回归测试`);
```

不支持任意 JS 的循环、if、await、文件/网络调用、require/import、成员方法、eval 或递归。遇到这些语法会报错，不悄悄降级成执行代码。

## 调用

```text
@continuous-development a("修复登录", "补回归测试")
@continuous-development b()
@continuous-development c("ecom")
@continuous-development auto("60s", 1)
```

`a()` 的两项任务按顺序展开。计划本身不调用模型、不改文件；执行阶段遵循既有权限、验证和 Git 规则。只读 `b()` 不会开始开发。

使用 `$` 提及 Skill 的界面改为 `$continuous-development`。这些函数名是本 Skill 的命令约定，不是 Codex 原生新注册的 API。

## 不记得命令时

```text
@continuous-development commands()
@continuous-development suggest("a")
@continuous-development a
@continuous-development wa
@continuous-development a(
@continuous-development a("修复登录",
```

发送 `a`：返回 `a(b, c)`、`auto(every = "60s", threshold = 1)`、`always()` 等实际匹配项，包含说明；不执行。
发送 `a(`：显示函数签名和第一个参数。
发送 `a("修复登录",`：提示第二个参数。
发送 `wa`：提示 `watch(...)`。
参数提示支持 `watch({thr` → `threshold: 1`、旧命令 `watch(thr` → `threshold=1`，以及 `watch("doc` → `doctor`。

提示从当前文件生成，不把 a/b/c 固定成前端、后端或游戏代理。输入完整调用才生成计划；拼写错误、缺参数或语法错误不会默认“全选并运行”。

## 定义并保存

发送包含 `const` 的定义默认只校验预览，不运行，也不静默覆盖命令表。
要保存可以明确告诉 Codex：

```text
请把下面的箭头函数注册到当前 Skill 的 commands/shortcuts.js。
先读取并保留其他命令，校验没有重名，备份后保存；不要执行函数、不要提交或推送。
const repair = target => task(`修复 ${target} 并添加回归测试`);
```

下一次 `repair` 的提示会从新定义生成。若函数文件本身格式有误，先修复文件，不伪造候选。

## 安装 / 更新

这份目录已按上传的仓库原结构合并，`SKILL.md` 和 `scripts/parse_invocation.py` 已接入 JS 路由。
不需要外层扩展目录、桌面 .command 文件或 `install_js_extension.py`。

先备份现有仓库，在原来的 `continuous-development/` 目录中合并同路径文件。
保留 `.git` 和个人修改；已有 `commands/shortcuts.js` 时不要覆盖。
新增的 `commands/shortcuts.example.js` 是示例，缺少自定义注册表时作为默认。
不要多套一层 `continuous-development/continuous-development/`，也不要把 ZIP 当成已安装的 Skill。

只在新 JS 功能被调用时需要本地 Node.js；Acorn 已随包提供，无需 npm install。
当前命令仅解析或提供提示，真实开发、Git 和后台操作仍需宿主工具及现有权限。

## 解析自检

将以下目录换成实际安装位置：

```bash
cd "$HOME/.codex/skills/continuous-development"
python3 scripts/parse_invocation.py '@continuous-development a'
python3 scripts/parse_invocation.py '@continuous-development a("修复登录","补测试")'
python3 scripts/parse_invocation.py '@continuous-development check()'
python3 scripts/complete_command.py '@continuous-development watch({thr'
```

上述命令只打印 JSON。`execution: not_executed` 表示没有执行开发或后台动作。

## 真正的实时输入框补全怎么接

客户端在输入变化后调用本地只读 provider：

```bash
python3 scripts/complete_command.py '@continuous-development a'
```

或直接启动 Node 读取一条 stdin JSON：

```json
{"action":"complete","text":"@continuous-development a","cursor":25}
```

命令：`node scripts/js_commands.cjs`。这里 cursor 是 JS/DOM UTF-16 偏移；不提供时为文本末尾。输入有其他长度时应提供真实光标值，不硬编码 25。

响应包含：
- `items[].label`：名称和签名。
- `items[].detail`：用途说明。
- `items[].insertText`：普通编辑框插入内容。
- `items[].insertSnippet`：支持 snippets 的编辑器可选择使用。
- `items[].replace.start/end`：应替换的范围，UTF-16，左闭右开。
- `signature`：函数签名、参数名和当前参数位置。
- `execution: not_executed`：提示接口绝不执行命令。

客户端需要自行监听输入/光标变化、做短暂防抖、渲染菜单、↑↓选项、Tab填入、Esc关闭，并丢弃过期响应。选择候选只填回文本，不自动发消息或执行命令。不能把源码或参数通过不受控的 shell 字符串传入进程。

本扩展没有修改 Codex/Codex++ 客户端，因此不能承诺在原生聊天输入框里边打字边弹窗。已实现的是可接入的 provider 和发送后提示。

## 与已有功能的关系

- 保留 watch、sessions、handoff、open、sync、Sub-agent、always/run 等已有规则。
- 新增前置路由只处理 JS 定义、已注册别名、命令查询和不完整输入。
- 既有 Python 管道继续原路径，不自动把其中的名字解释成 JS 别名。
- JS 对象选项会转为既有管理校验器接受的命令意图；例如 watch({retry:999}) 会被拒绝。
- 为保留安全边界，修改型 watch/sessions/sync 在一个别名中必须是唯一一步。
- 这一版没有建立任意 Node 执行沙箱；采用的是静态白名单，根本不运行用户 JS。

## 核对来源与验证边界

扩展对照了仓库当前 `scripts/parse_invocation.py`，blob `7e9da2e2dcc0115e1dbeb4385a83421a8aea73fc`，并以本次上传的 continuous-development-main.zip 为合并基线；不以旧 README 覆盖 EXAMPLES.md。

官方资料：
- Skill 是指令、资源、脚本的组合；技能提及与客户端能力分开：https://developers.openai.com/codex/skills/
- App Server 提供 skills/list 等集成接口，不代表已有任意参数输入补全控件：https://developers.openai.com/codex/app-server/
- JS 箭头函数语法：https://tc39.es/ecma262/multipage/ecmascript-language-functions-and-classes.html#sec-arrow-function-definitions
- AST 解析依赖 Acorn：https://github.com/acornjs/acorn

本机单元测试不等于用户 Mac/Codex 的实机测试。没有修改远程仓库，也没有在用户电脑安装任何服务。
