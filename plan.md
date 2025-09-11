# Claude 3.7/4 支持计划

## 现状分析

当前系统仅支持Claude 3.x系列模型，使用传统的InvokeModel API。Claude 3.7和Claude 4引入了新的推理能力（thinking模式）和budget参数，需要使用Converse API而非InvokeModel API。

### 关键差异

1. **API调用方式**：
   - 现有：`bedrock.invoke_model()` 
   - 新版：`bedrock.converse()` 

2. **推理配置**：
   - 新增：`additionalModelRequestFields` 包含thinking配置
   - 新增：`budget_tokens` 参数控制推理token预算

3. **响应结构**：
   - 新增：`ReasoningContentBlock` 包含推理过程
   - 变更：响应解析逻辑需要处理推理内容

## 实施计划

### Phase 1: 基础架构准备
- [ ] 在`task_executor.py`中添加新的模型ID映射
- [ ] 创建新的`invoke_claude37_claude4()`函数
- [ ] 修改`invoke_bedrock()`函数支持新模型分支

### Phase 2: API调用实现  
- [ ] 实现Converse API调用逻辑
- [ ] 添加推理配置参数处理
- [ ] 实现响应解析，分离推理内容和最终回答

### Phase 3: 配置和参数
- [ ] 添加环境变量`THINKING_BUDGET_TOKENS`（默认2000）
- [ ] 在规则YAML中支持`thinking_budget`字段
- [ ] 更新模型枚举值支持新模型

### Phase 4: 结果处理
- [ ] 修改结果存储结构，包含推理过程
- [ ] 更新报告模板显示推理内容
- [ ] 保持向后兼容性

### Phase 5: 测试和文档
- [ ] 添加新模型的集成测试
- [ ] 更新文档说明新模型使用方法
- [ ] 验证现有模型功能不受影响

## 技术细节

### 新增模型ID映射
```python
# 在invoke_bedrock()中添加
elif model == 'claude3.7-sonnet':
    llm_id = 'anthropic.claude-3-7-sonnet-20250219-v1:0'
elif model == 'claude4-opus':
    llm_id = 'anthropic.claude-opus-4-20250514-v1:0'
elif model == 'claude4-opus-4.1':
    llm_id = 'anthropic.claude-opus-4-1-20250805-v1:0'
elif model == 'claude4-sonnet':
    llm_id = 'anthropic.claude-sonnet-4-20250514-v1:0'
```

### Converse API调用结构
```python
# 推理配置
reasoning_config = {
    "thinking": {
        "type": "enabled",
        "budget_tokens": budget_tokens
    }
}

# API调用
response = bedrock.converse(
    modelId=llm_id,
    messages=messages,
    additionalModelRequestFields=reasoning_config
)
```

### 响应处理
```python
# 解析推理内容和最终回答
reasoning_text = None
final_text = None

for block in response['output']['message']['content']:
    if 'reasoningContent' in block:
        reasoning_text = block['reasoningContent']['text']
    elif 'text' in block:
        final_text = block['text']
```

## 风险评估

- **低风险**：新功能独立实现，不影响现有Claude 3.x模型
- **中风险**：需要测试Converse API在不同区域的可用性
- **注意事项**：Claude 3.7/4模型目前仅在部分区域可用（主要是us-east-1）

## 预期收益

1. **增强推理能力**：用户可以看到AI的思考过程
2. **更好的代码评审质量**：推理模式有助于更深入的分析
3. **灵活的token控制**：通过budget参数控制推理深度
4. **向前兼容**：为未来更多推理模型做准备
