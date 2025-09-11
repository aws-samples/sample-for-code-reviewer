#!/bin/bash
set -e

echo "=== Code Reviewer CDK 部署脚本 ==="

# 检查Node.js和npm
echo "检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo "错误: 未找到Node.js，请先安装Node.js"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "错误: 未找到npm，请先安装npm"
    exit 1
fi

echo "Node.js版本: $(node --version)"
echo "npm版本: $(npm --version)"

# 安装npm依赖
echo "安装npm依赖..."
npm install

# 构建TypeScript
echo "构建TypeScript..."
npm run build

# 构建Lambda layers
echo "构建Lambda layers..."
./scripts/build-layer.sh

# 检查layer文件是否存在
echo "检查layer文件..."
if [ ! -f "layer/common-layer.zip" ]; then
    echo "错误: layer/common-layer.zip 不存在"
    exit 1
fi

if [ ! -f "layer/gitlab-layer.zip" ]; then
    echo "错误: layer/gitlab-layer.zip 不存在"
    exit 1
fi

if [ ! -f "layer/github-layer.zip" ]; then
    echo "错误: layer/github-layer.zip 不存在"
    exit 1
fi

echo "所有layer文件检查通过"

# CDK部署
echo "开始CDK部署..."

# 选择以下命令之一，取消注释即可使用：

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

echo "=== CDK部署完成 ==="
echo "请参考INSTALL-CDK.md文档完成后续配置步骤："
echo "1. 配置数据库"
echo "2. 配置GitLab/GitHub"
echo "3. 验证部署"
