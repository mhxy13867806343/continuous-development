# JS 箭头函数与命令提示：设计与执行记录

## 用户目标
支持 `const a=(b,c)=>{...}`、`const b=()=>{...}`、`const b=c=>{...}` 的命令别名定义；不必记住所有命令，可以根据前缀查询函数名称和参数。

## 本次选择
采用 Acorn 8.15.0 静态解析 JS AST，加严格白名单展开为命令计划；不 eval，不加载执行用户 JS，不开放任意 Node 能力。保留原来的 Python 解析及 watch/sessions 等功能。
支持参数、字面量默认值、模板字符串和顺序调用。复杂 JS 如循环、await、动态 import、类、赋值、成员方法调用不在这一版范围。

只写 Markdown 不能给未改造的 Codex 输入框增加键盘监听。交付：本地补全接口 + 发送后的只读提示 + 客户端接入协议。未交付：原生 Codex/Codex++ 输入框插件。
不将 CLI 输出的命令计划标记为已经启动后台服务。

## 文件设计
- scripts/js_commands.cjs：安全 AST / 别名展开 / 补全 JSON。
- scripts/js_command_bridge.py：调用本地 Node、校验既有管理命令、向 Python 入口提供前置路由。
- commands/shortcuts.example.js：三种箭头形态与实用示例；不存在用户文件时以示例为默认，不覆盖用户 shortcuts.js。
- commands/shortcuts.js：由用户自行维护的可选注册表；只读取文本，不 require。
- js-commands.md、README-JS-COMMANDS.md：规则与使用边界。
- install_js_extension.py：带备份的局部安装，默认预览，无 Git 或定时副作用。

## 验收
1. 三种定义形态均可静态解析；重复 const 名称报错。
2. 只输入名称/前缀时只返回候选；已输入 `(` 时给参数提示。
3. 定义只预览；完整调用只返回计划，不启动后台服务、不提交代码。
4. 拒绝 eval/require/成员访问/无限循环/未知命令/递归/原型键。
5. watch/sessions/open/sync 的实际参数继续交给已有校验器。
6. 原有 Python 单元测试回归；安装预览、备份、重复安装验证。
7. 明确原生输入框补全尚未接入、真实 Mac 未实测。

## 实施计划
先写失败测试，再实现 Node 解析器和 Python 桥接；执行新旧测试；生成下载包和验证记录。修改仅在工作区进行，不提交或推送远程。
