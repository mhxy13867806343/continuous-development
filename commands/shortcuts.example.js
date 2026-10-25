// 这是受限的 JS 命令定义，不是任意 Node.js 执行文件。
// 自定义时复制为同目录 shortcuts.js；解析器只读取文本，不 require 此文件。

/** 按顺序处理两项明确任务。示例：a("修复登录", "补回归测试") */
const a = (b, c) => {
  task(b);
  task(c);
};

/** 查看状态。零参数箭头函数示例 */
const b = () => {
  status();
};

/** 查看某个项目的进度。单参数省略括号示例 */
const c = project => {
  open(project);
};

/** 后台续作快捷方式；选项仍由 watch 原有规则校验 */
const auto = (every = "60s", threshold = 1) => {
  watch({every, retry: 3, threshold});
};

/** 只做后台环境检查，不启动开发 */
const check = () => watch("doctor");
