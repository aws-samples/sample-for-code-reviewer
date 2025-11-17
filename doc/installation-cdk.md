# CDK安装法

## 说明

本文介绍如何通过CDK的方式安装Code Reviewer方案，CDK的方法相对与CloudFormation方法更加复杂，但是适合Code Reviewer项目迭代。如果你需要二次开发Code Reviewer，涉及到架构变更，涉及反复迭代，CDK的开发和部署方法是非常合适的。

如果你只是试用Code Reviewer，推荐使用CloudFormation的安装方法，具体可参看《[CloudFormation安装法](INSTALL.md)》

## 启动Cloud9

进入Cloud9服务，启动一台Cloud9，表单如下：
```
Name = code-reviewer-cloud9
Instance type = t2.micro
Platform = Amazon Linux 2023
Timeout = 按自己的需求
Connection = AWS System Manager(SSM)
```

创建成功后，点击Open按钮打开Cloud9的IDE，在IDE中关闭不必要的Tab，通过`Window`菜单的`New Terminal`打开一个新的Terminal。注意，IDE中的Window都是可以拖动和放大的。

说明：Cloud9是一个具有Web IDE的ec2，已经预装了各种开发环境。使用Cloud9可以避免在自己本地安装不必要的软件，另外随处打开Cloud9 IDE都能保持上次的编辑状态。Cloud9具有免费额度，因此不用担心费用问题。

> 功能路径：Cloud9服务 / 左侧菜单My environments / 点击右侧Create environment按钮

## CDK的必要准备

在Terminal中执行以下命令：

```shell
# 注意修改AWS_DEFAULT_REGION参数
export AWS_DEFAULT_REGION=us-west-2
export ACCOUNT_ID=`aws sts get-caller-identity --query Account --output text`
cdk bootstrap aws://$ACCOUNT_ID/$AWS_DEFAULT_REGION
```

## 克隆Github项目

在Terminal中执行以下命令clone项目：

```shell
# 注意修改BRANCH这一项
export BRANCH=dev
git clone https://github.com/aws-samples/sample-for-code-reviewer.git
cd sample-for-code-reviewer
git checkout $BRANCH
```

其中`BRANCH`代表Github上的分支，你可以根据github上的信息选取适合你的分支。

## CDK部署项目

### 方法一：一键部署脚本（推荐）

使用自动化部署脚本：

```shell
./scripts/deploy-cdk.sh
```

该脚本会自动执行：
1. 检查Node.js和npm环境
2. 安装npm依赖
3. 构建TypeScript代码
4. 构建所有Lambda layers
5. 验证layer文件存在
6. 执行CDK部署

**自定义参数**：如需修改项目名称或其他参数，请编辑 `scripts/deploy-cdk.sh` 文件，取消注释相应的CDK命令行。

### 方法二：手动部署

如果需要手动控制每个步骤：

```shell
# 1. 安装依赖
npm install

# 2. 构建TypeScript
npm run build

# 3. 构建Lambda layers
./scripts/build-layer.sh

# 4. CDK部署（选择以下命令之一）

# 默认参数部署
npm run cdk -- deploy --require-approval never

# 自定义项目名称
# npm run cdk -- deploy --require-approval never --parameters ProjectName=my-code-reviewer

# 完整自定义参数示例
# npm run cdk -- deploy --require-approval never \
#   --parameters ProjectName=my-code-reviewer \
#   --parameters EnableApiKey=true \
#   --parameters SMTPServer=smtp.example.com \
#   --parameters SMTPPort=587
```

**重要**：无论使用哪种方法，都必须确保以下文件存在：
- `layer/common-layer.zip`
- `layer/gitlab-layer.zip` 
- `layer/github-layer.zip`

⚠️ 注意：如果出现结构性的调整，例如修改Dynamodb Table PK/SK，CDK不会删除S3 Bucket和DynamoDB，你需要自行删除这些资源才能重新部署。

## 配置GitLab（可选） 

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 配置GitLab](installation.md#配置gitlab可选)》一节

## 配置GitHub（可选）

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 配置GitHub](installation.md#配置github可选)》一节

## 验证

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 验证](installation.md#验证)》一节

## 清理Cloud9

完成部署后，你可以选择关闭Cloud9

> 功能路径：Cloud9服务 / 左侧菜单My environments / 选中Cloud9点击右侧Delete按钮