# CHANGELOG

## v1.5.1

- Add: 文档中增加版本升级方法说明

## v1.5

- Add: Claude 3.7/4/4.5 支持
- Add: Web Tool 中的 Extended Thinking 配置界面（启用复选框 + token 预算输入）
- Changed: 输出格式顺序从 <output><thought> 改为 <thought><output>
- Changed: Simulation library 增强，根据模型后缀过滤Commit文件

## v1.3

- Add: GitHub仓库支持，包含完整API集成
- Add: 完整测试框架，支持自动化测试数据推送、验证和端到端测试
- Add: 模块化Lambda层构建系统和CDK一键部署脚本
- Add: 完整的技术架构文档和业务流程说明
- Add: 大量模拟测试数据用于多场景测试验证
- Changed: Web界面支持GitHub仓库配置
- Changed: 后端架构支持多平台仓库操作

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
