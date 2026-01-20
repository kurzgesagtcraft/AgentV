# KiloMemoryMCP VCP集成版迁移指南

## 概述

本文档指导您如何从旧版KiloMemoryMCP迁移到新的VCP集成版，以解决"回忆能力太烂"的问题。

## 问题分析

### 旧版本问题
1. **回忆能力差**：主要依赖SQL LIKE查询，缺乏语义理解
2. **重复结果**：去重机制有问题，显示重复内容
3. **主动回忆失败**：改进的回忆系统未正确集成
4. **向量搜索未充分利用**：模拟实现，未真正集成VCP能力
5. **记忆质量评估简单**：基于简单规则，缺乏深度学习

### 新版本改进
1. **直接集成VCP向量搜索**：使用KnowledgeBaseManager进行真正的语义搜索
2. **使用TagMemo语义扩展**：实现真正的语义理解
3. **优化去重机制**：基于内容哈希去重
4. **实现真正的"一次回忆起"**：`trigger_vcp_recall`工具
5. **改进质量评估**：结合向量相似度和内容结构
6. **提供搜索统计**：显示VCP向量搜索和文件系统搜索的结果

## 迁移步骤

### 步骤1：备份现有配置
```bash
# 备份当前的MCP设置
cp "c:/Users/kurzcraft/AppData/Roaming/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json" "c:/Users/kurzcraft/AppData/Roaming/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json.backup"
```

### 步骤2：更新MCP服务器配置
编辑MCP设置文件，将KiloMemoryMCP服务器指向新的VCP集成版：

```json
{
  "mcpServers": {
    "KiloMemoryMCP": {
      "command": "python",
      "args": ["D:/vscode/AgentV/KiloMemoryMCP/kilo_memory_server_vcp_integrated.py"],
      "alwaysAllow": [
        "store_kilo_memory",
        "query_kilo_memory", 
        "trigger_vcp_recall",
        "list_all_kilo_memories",
        "get_memory_stats"
      ],
      "disabled": false,
      "autoStart": true,
      "description": "Kilo Code VCP集成版记忆系统 - 支持真正的语义搜索和主动回忆"
    }
  }
}
```

### 步骤3：重启VSCode或重新加载MCP服务器
1. 重启VSCode，或
2. 使用命令面板执行"Kilo Code: Reload MCP Servers"

## 新工具使用指南

### 1. store_kilo_memory
存储记忆到VCP系统，会被KnowledgeBaseManager自动索引。

```python
# 示例
store_kilo_memory(
    content="我的电脑配置是ROG Strix G834JY，搭载i9-13980HX和RTX 4090",
    tags=["硬件配置", "ROG Strix", "电脑信息"]
)
```

### 2. query_kilo_memory
使用VCP向量搜索查询记忆，支持语义扩展。

```python
# 示例 - 会自动扩展"电脑"到"计算机"、"硬件"等概念
query_kilo_memory("电脑硬件", limit=5, min_quality=0.5)
```

### 3. trigger_vcp_recall
在任务开始时自动触发回忆，实现"一次回忆起"。

```python
# 示例 - 在任务开始时调用
trigger_vcp_recall(
    user_message="我想了解我的电脑硬件配置",
    system_context="用户需要硬件信息"
)
```

### 4. list_all_kilo_memories
列出最近的记忆。

```python
# 示例
list_all_kilo_memories(limit=20)
```

### 5. get_memory_stats
获取记忆系统统计信息。

```python
# 示例
get_memory_stats()
```

## 最佳实践

### 1. 为记忆添加详细标签
```python
# 好例子
store_kilo_memory(content, tags=["硬件配置", "ROG Strix", "Windows 11", "系统信息"])

# 坏例子  
store_kilo_memory(content, tags=[])  # 无标签，难以检索
```

### 2. 在任务开始时使用主动回忆
```python
# 在Kilo Code的任务开始时调用
trigger_vcp_recall(user_message=当前任务描述)
```

### 3. 使用语义查询而非关键词
```python
# 好例子 - 使用自然语言
query_kilo_memory("如何优化Windows 11性能")

# 坏例子 - 使用过于具体的关键词
query_kilo_memory("Windows 11 性能 优化 步骤")
```

### 4. 定期检查系统状态
```python
# 定期运行
get_memory_stats()
```

## 故障排除

### 问题1：VCP向量搜索不可用
```
⚠️ VCP向量搜索不可用: No module named 'KnowledgeBaseManager'
```

**解决方案**：
1. 确保VCP系统正在运行
2. 检查`modules/KnowledgeBaseManager.js`文件是否存在
3. 确保Python可以导入该模块

### 问题2：主动回忆未触发
**解决方案**：
1. 检查查询关键词是否太模糊
2. 确保有相关的记忆存在
3. 尝试降低质量阈值：`min_quality=0.3`

### 问题3：查询结果不准确
**解决方案**：
1. 使用更具体的查询词
2. 为记忆添加更多相关标签
3. 使用`get_memory_stats()`检查系统状态

## 性能优化

### 1. 调整查询参数
```python
# 平衡准确性和性能
query_kilo_memory(query, limit=10, min_quality=0.4)
```

### 2. 批量存储记忆
```python
# 批量存储相关记忆
for memory in memories:
    store_kilo_memory(memory.content, memory.tags)
```

### 3. 使用缓存
系统会自动缓存频繁访问的记忆，提高查询速度。

## 与VCP系统的集成

### 1. 知识共享
VCP集成版会自动将记忆共享到VCP的知识库中，其他AI Agent也可以访问。

### 2. 向量索引
记忆会被自动向量化并建立索引，支持快速的语义搜索。

### 3. 标签系统
使用VCP的TagMemo系统进行语义扩展，提高检索准确性。

## 监控和维护

### 1. 定期检查
```bash
# 检查记忆文件数量
ls -la d:/vscode/AgentV/dailynote/KiloMemory/ | wc -l
```

### 2. 清理旧记忆
```python
# 使用get_memory_stats()查看系统状态
# 根据需要清理旧的不重要记忆
```

### 3. 优化标签
定期检查和优化记忆标签，提高检索效率。

## 结论

通过迁移到VCP集成版，KiloMemoryMCP的回忆能力将得到显著提升：

1. ✅ **真正的语义搜索**：不再是简单的关键词匹配
2. ✅ **智能查询扩展**：自动扩展相关概念  
3. ✅ **主动回忆**：在任务开始时自动提供相关记忆
4. ✅ **透明统计**：显示搜索方法和结果来源
5. ✅ **易于扩展**：基于VCP生态系统，可与其他工具集成

迁移过程简单快捷，只需更新MCP服务器配置即可享受改进的回忆能力。