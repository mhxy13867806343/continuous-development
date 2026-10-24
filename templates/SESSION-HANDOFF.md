# 会话交接

> 模板：所有占位内容必须由真实观测填写；unknown 优于猜测。

## 来源与恢复

- provider / account：<真实来源；不记录 token>
- project_id / project_name：<真实值>
- workspace：<本地路径；默认不公开上传>
- source_thread_id：<真实ID>
- 来源链接：<宿主提供的可验证链接；没有则留空>
- 可复制 Markdown：`[聊天对话串](<真实来源URI>)`（没有URI时不伪造）
- target_thread_id：<仅真实创建后填写>
- rollover_operation_id：<幂等事务ID>
- observed_at：<含时区时间>

## 任务

- 当前目标：
- 验收标准：
- 已验证完成：
- 正在执行/尚未完成：
- 阻塞/需人工确认：
- 下一步（明确第一步）：

## 文件和验证

- 关键文件：
- 执行的检查及结果：
- 未执行的检查及原因：
- 数据/迁移/部署风险：

## Git

- 分支 / HEAD：
- 未提交改动与归属：
- 已验证 checkpoint SHA：
- 各远程推送状态与查询时间：
- 绝不混入的用户改动：

## 生命周期与额度

- 已观测轮数 / 阈值（未知则unknown）：
- 停止派新任务原因：
- 剩余额度及来源/采样时间（未知则unknown）：
- 归档状态及验证：
- 新建状态及验证：
- 恢复条件：

## 隐私检查

不得附加密码、Cookie、API Key、OAuth 凭证或无关聊天记录。
