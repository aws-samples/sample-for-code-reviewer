#!/bin/bash
set -e

echo "Building all Lambda layers..."

# Common Layer
echo "Building Common Layer..."
rm -rf layer/common-layer.zip tmp/python
mkdir -p tmp/python

pip install --target tmp/python --platform linux_x86_64 --python-version 3.12 --only-binary=:all: boto3 requests typing_extensions
pip install --target tmp/python --platform linux_x86_64 --python-version 3.12 --no-deps PyYAML

cd tmp
zip -r ../layer/common-layer.zip python/
cd ..
echo "Common layer complete: layer/common-layer.zip"

# GitLab Layer
echo "Building GitLab Layer..."
rm -rf layer/gitlab-layer.zip tmp/python
mkdir -p tmp/python

pip install --target tmp/python --platform linux_x86_64 --python-version 3.12 --only-binary=:all: python-gitlab

cd tmp
zip -r ../layer/gitlab-layer.zip python/
cd ..
echo "GitLab layer complete: layer/gitlab-layer.zip"

# GitHub Layer
echo "Building GitHub Layer..."
rm -rf layer/github-layer.zip tmp/python
mkdir -p tmp/python

pip install --target tmp/python --platform linux_x86_64 --python-version 3.12 --only-binary=:all: "PyGithub"

cd tmp
zip -r ../layer/github-layer.zip python/
cd ..
rm -rf tmp
echo "GitHub layer complete: layer/github-layer.zip"

echo "All layers built successfully!"
