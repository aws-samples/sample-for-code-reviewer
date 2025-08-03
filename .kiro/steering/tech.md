# 技术栈

## 基础设施与部署
- **AWS CDK**: 使用TypeScript的基础设施即代码 (CDK v2)
- **CloudFormation**: 替代部署方法
- **Node.js**: CDK构建系统，支持TypeScript编译

## 后端服务
- **AWS Lambda**: 所有无服务器函数使用Python 3.13运行时
- **Amazon Bedrock**: 使用Claude 3模型 (Opus, Sonnet, Haiku) 进行AI代码分析
- **API Gateway**: REST API端点，支持可选的API密钥认证
- **Amazon SQS**: Bedrock任务处理的异步任务队列
- **Amazon SNS**: 报告投递的通知系统
- **Amazon DynamoDB**: 用于请求/任务状态管理的NoSQL数据库
- **Amazon S3**: 存储生成的报告和静态资源

## 前端
- **原生JavaScript**: 无框架的Web工具界面
- **HTML/CSS**: 静态Web界面
- **第三方库**: Axios (HTTP请求), js-yaml (YAML解析)

## Python依赖

### Lambda层依赖 (layer.zip)
主要引入的核心模块：
- **boto3**: AWS SDK，用于访问AWS服务
- **python-gitlab**: GitLab API集成客户端
- **requests**: HTTP请求库
- **PyYAML**: YAML配置文件解析

其他模块（如botocore、s3transfer、certifi、urllib3等）为上述核心模块的依赖，会自动安装。

### 自定义模块
- **组织结构**: 位于lambda/目录中
- **层管理**: layer.zip预构建，更新需重新打包依赖
- **兼容性**: 支持Python 3.13运行时
- **可扩展设计**: 通过codelib.py抽象仓库集成，为未来GitHub/CodeCommit支持预留接口
  - 当前设计：每个动作定义一个function，通过if-else分流不同source
  - 设计不足：应该使用更标准的接口实现模式，未来需要重构

## 项目配置
- **项目名称**: 通过CDK CloudFormation参数`ProjectName`设置，默认值为`aws-code-reviewer`
- **资源命名**: 所有AWS资源名称使用`{project_name}-{resource_type}`格式
- **API密钥**: 可选配置，通过`EnableApiKey`参数控制
- **SMTP配置**: 支持邮件通知，需配置SMTPServer、SMTPPort、SMTPUsername、SMTPPassword等参数
- **Bedrock配置**: 可选配置访问密钥、密钥和区域参数
- **语言支持**: 语言无关，Claude模型可理解多种编程语言，通过prompt_system和prompt_user字段自定义评审规则

## 运维配置
- **SQS队列**: 使用默认配置，未设置死信队列
- **S3存储**: 使用标准存储层，无自动清理策略
- **GitLab API**: 无速率限制处理，适用于内部系统使用
- **Lambda资源**: 使用默认内存和超时配置
- **并发限制**: 不支持多分支并行评审

## 常用命令

### 开发与测试
```bash
# 安装依赖
npm install

# 构建TypeScript
npm run build

# 开发监听模式
npm run watch

# 运行测试
npm test

# CDK命令
npm run cdk -- deploy
npm run cdk -- diff
npm run cdk -- destroy
```

### 本地开发
```bash
# 模拟仓库事件进行测试
python scripts/mock_codelib_event.py

# 直接测试Bedrock集成
python scripts/invoke_bedrock_youself.py
```

## 构建系统
- 通过`tsc`进行TypeScript编译
- Lambda层通过layer.zip包含4个核心Python模块及其依赖
- CDK合成CloudFormation模板
- Lambda函数和层的资源打包
- 层描述: "This layer includes pyyaml, python-gitlab module."