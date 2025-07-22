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
- **boto3**: AWS SDK
- **pyyaml**: YAML配置解析
- **python-gitlab**: GitLab API集成 (主要实现)
- **自定义模块**: 组织在lambda/目录中
- **可扩展设计**: 通过codelib.py抽象仓库集成，为未来GitHub/CodeCommit支持预留接口

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
- Lambda打包通过layer.zip包含Python依赖
- CDK合成CloudFormation模板
- Lambda函数和层的资源打包