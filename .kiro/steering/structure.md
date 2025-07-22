# 项目结构

## 根目录组织
```
├── bin/                    # CDK入口点
├── lib/                    # CDK堆栈定义 (TypeScript)
├── lambda/                 # Lambda函数源代码 (Python)
├── layer/                  # Lambda层依赖
├── scripts/                # 开发和测试工具
├── test/                   # 单元测试
└── webtool/                # 静态Web界面
```

## CDK基础设施 (`lib/`)
- **code-reviewer-stack.ts**: 主堆栈编排器
- **api-stack.ts**: API Gateway和Lambda函数
- **bucket-stack.ts**: S3存储桶配置
- **database-stack.ts**: DynamoDB表
- **sqs-stack.ts**: SQS队列设置
- **sns-stack.ts**: SNS主题配置
- **cron-stack.ts**: 定时任务
- **nag-suppressions.ts**: CDK安全规则例外

## Lambda函数 (`lambda/`)

### 核心处理
- **request_handler.py**: Webhook接收器，创建请求记录
- **task_dispatcher.py**: 将请求分解为Bedrock任务
- **task_executor.py**: SQS消费者，执行Bedrock调用
- **result_checker.py**: 进度跟踪和状态查询
- **report_receiver.py**: SNS消费者，发送通知

### 仓库集成
- **codelib.py**: 抽象仓库接口
- **gitlab_code.py**: GitLab特定实现
- **rule_loader.py**: 从仓库获取评审规则
- **rule_updater.py**: 更新仓库规则文件

### 工具类
- **base.py**: 通用函数、日志、JSON处理
- **task_base.py**: 共享任务管理逻辑
- **logger.py**: 结构化JSON日志配置
- **report.py**: HTML报告生成
- **cron_function.py**: 清理和超时处理

### 配置与模板
- **report_template.html**: 代码评审报告的HTML模板
- **repos.json**: DynamoDB设置的初始仓库配置
- **rules.json**: DynamoDB初始化的默认评审规则
- **data_initializer.py**: 将repos.json和rules.json处理到DynamoDB表中
- **cloudfront_func.js**: Web工具路由的CloudFront函数

## Web工具 (`webtool/`)
- **index.html**: 主界面
- **script.js**: 应用程序入口点
- **custom.js**: API通信
- **section.js**: 左侧面板UI组件
- **result.js**: 右侧面板结果显示
- **progress.js**: 进度跟踪UI
- **template.*.yaml**: 评审规则模板

## 命名约定
- Lambda函数: `{project_name}-{function_name}`
- DynamoDB表: `{project_name}-{table_type}`
- S3存储桶: `{project_name}-{bucket_purpose}`
- Python模块: snake_case
- TypeScript文件: kebab-case
- CDK构造: PascalCase，带CR前缀 (例如: CRApi, CRDatabase)

## 配置文件
- **cdk.json**: CDK应用程序配置
- **package.json**: Node.js依赖和脚本
- **tsconfig.json**: TypeScript编译器选项
- **.gitignore**: 版本控制排除项