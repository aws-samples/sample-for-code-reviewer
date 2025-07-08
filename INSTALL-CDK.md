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
git clone https://github.com/wengkaer/code-reviewer.git
cd code-reviewer
git checkout $BRANCH
npm install
```

其中`BRANCH`代表Github上的分支，你可以根据github上的信息选取适合你的分支。	


## CDK部署项目

下面三个命令，选择一个运行：
```
# 使用默认参数，必要时输入y确认
cdk deploy

# 使用默认参数，避开询问
# cdk deploy --require-approval never

# 自定义参数，你可以自行修改ProjectName等参数
# cdk deploy --require-approval never --parameters ProjectName=code-review-demo 
```

⚠️ 注意：如果出现结构性的调整，例如修改Dynamodb Table PK/SK，CDK不会删除S3 Bucket和DynamoDB，你需要自行删除这些资源才能重新部署。

## 配置数据库

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 配置数据库](INSTALL.md#配置数据库)》一节

## 配置Gitlab 

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 配置Gitlab](INSTALL.md#配置Gitlab)》一节

## 验证

与CloudFormation方式下方法相同，具体可参看《[CloudFormation安装法 - 验证](INSTALL.md#验证)》一节

## 清理Cloud9

完成部署后，你可以选择关闭Cloud9

> 功能路径：Cloud9服务 / 左侧菜单My environments / 选中Cloud9点击右侧Delete按钮