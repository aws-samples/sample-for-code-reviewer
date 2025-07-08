# CHANGELOG

## v1.2

- ADD: PE调试工具重命名为Web Tool
- MODIFY: 将DynamoDB的规则改为代码仓库下yaml文件规则
- ADD: Web Tool可直接读取和写入代码仓库下yaml规则
- ADD: 增加了评审后二次校验的能力

## v1.1

- ADD: 代码评审PE调试工具
- ADD: 基于EventBridge的每分钟定时任务清理失败任务
- REMOVE: Lambda+SQS自嵌套方式清理失败任务
- MODIFY: 评审报告中去除level
- MDOIFY: Bedrock响应格式变化
- MODIFY: 可选的API Key，默认不启用

## V1.0

- 打通Gitlab
- 整库代码评审
- 单文件代码评审