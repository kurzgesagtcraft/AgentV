# KiloMemoryMCP 增强版迁移指南

## 概述

本文档指导您从原始 KiloMemoryMCP 迁移到增强版 KiloMemoryMCP。增强版在保持完全向后兼容的同时，提供了记忆进化、质量评估、知识图谱等高级功能。

## 迁移前准备

### 1. 备份现有数据

```bash
# 备份记忆文件
cp -r dailynote/KiloMemory dailynote/KiloMemory_backup_$(date +%Y%m%d)

# 备份数据库（如果存在）
cp VectorStore/knowledge_base.sqlite VectorStore/knowledge_base_backup_$(date +%Y%m%d).sqlite
```

### 2. 检查系统依赖

增强版需要相同的依赖环境：
- Python 3.8+
- mcp.server.fastmcp
- 现有的 KnowledgeBaseManager 系统
- Vexus-Lite 向量索引

## 迁移步骤

### 步骤1：安装增强版MCP

将新的 `kilo_memory_server_enhanced.py` 文件复制到 MCP 目录：

```bash
cp KiloMemoryMCP/kilo_memory_server_enhanced.py ../Roo_Code/MCP/KiloMemoryMCP/
```

### 步骤2：更新MCP配置

如果使用 MCP 配置文件，更新服务器路径：

```json
{
  "mcpServers": {
    "kilo-memory": {
      "command": "python",
      "args": [
        "d:/vscode/AgentV/Roo_Code/MCP/KiloMemoryMCP/kilo_memory_server_enhanced.py"
      ],
      "env": {
        "PYTHONPATH": "d:/vscode/AgentV"
      }
    }
  }
}
```

### 步骤3：初始化进化数据库

增强版首次运行时会自动创建进化数据库：

```bash
cd d:/vscode/AgentV
python Roo_Code/MCP/KiloMemoryMCP/kilo_memory_server_enhanced.py
```

系统将创建：
- `VectorStore/memory_evolution.sqlite`：进化跟踪数据库
- 必要的表结构和索引

### 步骤4：迁移现有记忆（可选）

如果您希望为现有记忆添加进化跟踪，运行迁移脚本：

```python
# migrate_existing_memories.py
import os
import sqlite3
from kilo_memory_server_enhanced import EnhancedMemoryManager

manager = EnhancedMemoryManager()

# 扫描现有记忆文件
memory_dir = "dailynote/KiloMemory"
for filename in os.listdir(memory_dir):
    if filename.endswith(".md"):
        filepath = os.path.join(memory_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取标签（从文件内容）
        tags = []
        if "Tag:" in content:
            tag_line = content.split("Tag:")[1].split("\n")[0].strip()
            tags = [t.strip() for t in tag_line.split(",")]
        
        # 重新分析并注册到进化系统
        result = manager.store_memory(content, tags)
        print(f"迁移: {filename} -> {result.get('memory_id', '失败')}")
```

## 功能对比

### 原始MCP功能

| 功能 | 原始MCP | 增强版MCP |
|------|---------|-----------|
| 记忆存储 | ✅ | ✅（增强格式） |
| 基本查询 | ✅ | ✅（质量过滤） |
| 文件列表 | ✅ | ✅（类型分类） |
| VCP集成 | ✅ | ✅ |

### 新增功能

| 功能 | 描述 | 使用方式 |
|------|------|----------|
| **记忆类型识别** | 自动识别6种记忆类型 | 存储时自动分析 |
| **质量评估** | 五维质量评分 | `query_kilo_memory(min_quality=0.6)` |
| **进化跟踪** | 记录记忆变化历史 | `get_memory_evolution_history(memory_id)` |
| **记忆进化** | 抽象化、精炼、融合 | `evolve_memory(memory_id, "abstract")` |
| **关联分析** | 发现记忆间关系 | `analyze_memory_network()` |
| **知识图谱** | 构建记忆网络 | 自动构建，可通过API查询 |
| **洞察报告** | 系统状态分析 | `get_memory_insights()` |

## API变化

### 保持兼容的API

以下API保持完全兼容：

```python
# 存储记忆（增强版支持更多参数）
store_kilo_memory(content: str, tags: List[str] = None) -> str

# 查询记忆（增强版支持质量过滤）
query_kilo_memory(query: str = "", limit: int = 10) -> str

# 列出记忆
list_all_kilo_memories(limit: int = 20) -> str
```

### 新增API

```python
# 记忆进化
evolve_memory(memory_id: str, evolution_type: str, new_content: str = None) -> str

# 获取进化历史
get_memory_evolution_history(memory_id: str) -> str

# 分析记忆网络
analyze_memory_network() -> str

# 获取系统洞察
get_memory_insights() -> str

# 带质量过滤的查询
query_kilo_memory(query: str = "", limit: int = 10, min_quality: float = 0.0) -> str
```

## 文件格式变化

### 原始格式

```markdown
# Kilo Memory - 2026-01-20T22:28:07.256675

系统配置信息...

Tag: 系统配置, 硬件信息
```

### 增强格式

```markdown
# Kilo Memory - 2026-01-20T22:28:07.256675
## 记忆ID: mem_20260120_abc123
## 记忆类型: fact
## 质量评分: 0.78

### 内容
系统配置信息...

### 元数据
- **标签**: 系统配置, 硬件信息
- **关键概念**: 系统配置, 硬件
- **清晰度**: 0.85
- **重要性**: 0.70
- **完整性**: 0.90
- **相关性**: 0.75
- **新颖性**: 0.70

### 进化跟踪
- 创建时间: 2026-01-20T22:28:07.256675
- 记忆哈希: a1b2c3d4

Tag: 系统配置, 硬件信息
```

**注意**：增强版完全兼容读取原始格式文件，新文件将使用增强格式。

## 配置选项

### 环境变量

增强版支持以下环境变量：

```bash
# 记忆进化配置
export MEMORY_EVOLUTION_ENABLED=true
export MAX_ABSTRACTION_LEVEL=3
export MIN_MEMORY_QUALITY=0.3

# 质量评估权重（0-1）
export QUALITY_WEIGHT_RELEVANCE=0.25
export QUALITY_WEIGHT_CLARITY=0.20
export QUALITY_WEIGHT_COMPLETENESS=0.15
export QUALITY_WEIGHT_IMPORTANCE=0.25
export QUALITY_WEIGHT_NOVELTY=0.15

# 关联分析
export RELATION_STRENGTH_THRESHOLD=0.7
export MAX_RELATIONS_PER_MEMORY=20
```

### 配置文件

可在 `KiloMemoryMCP/config.json` 中配置：

```json
{
  "evolution": {
    "enabled": true,
    "abstraction_levels": 3,
    "auto_abstract_threshold": 0.8,
    "quality_decay_days": 30
  },
  "quality_weights": {
    "relevance": 0.25,
    "clarity": 0.20,
    "completeness": 0.15,
    "importance": 0.25,
    "novelty": 0.15
  },
  "analysis": {
    "batch_size": 50,
    "concurrency": 4,
    "cache_ttl": 3600
  }
}
```

## 使用示例

### 示例1：基本使用（兼容模式）

```python
# 存储记忆（与原始MCP相同）
result = store_kilo_memory("Python虚拟环境配置方法...", 
                          tags=["Python", "开发环境"])

# 查询记忆（与原始MCP相同）
memories = query_kilo_memory("Python", limit=5)
```

### 示例2：使用增强功能

```python
# 存储并获取记忆ID
result = store_kilo_memory("深度学习训练技巧...", 
                          tags=["AI", "深度学习"])
# 结果包含记忆ID和质量评分

# 质量过滤查询
high_quality_memories = query_kilo_memory(
    "训练", 
    limit=10, 
    min_quality=0.7  # 只返回质量≥0.7的记忆
)

# 记忆进化
evolution_result = evolve_memory(
    memory_id="mem_20260120_abc123",
    evolution_type="abstract"  # 抽象化
)

# 获取进化历史
history = get_memory_evolution_history("mem_20260120_abc123")

# 分析记忆网络
network = analyze_memory_network()

# 获取系统洞察
insights = get_memory_insights()
```

### 示例3：批量处理

```python
# 批量迁移和分析现有记忆
import glob

memory_files = glob.glob("dailynote/KiloMemory/*.md")

for filepath in memory_files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 重新分析并增强
    result = store_kilo_memory(content)
    
    if result["success"]:
        print(f"✓ 增强: {os.path.basename(filepath)}")
        print(f"  类型: {result['metadata']['type']}")
        print(f"  质量: {result['metadata']['quality']['overall_score']:.2f}")
    else:
        print(f"✗ 失败: {os.path.basename(filepath)}")
```

## 故障排除

### 常见问题

#### Q1：增强版启动失败，提示缺少模块
**A**：确保安装了所有依赖：
```bash
pip install mcp.server.fastmcp dataclasses typing
```

#### Q2：现有记忆文件无法读取
**A**：增强版兼容原始格式，但如果文件编码有问题，尝试：
```python
# 修复文件编码
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
```

#### Q3：进化数据库创建失败
**A**：检查目录权限：
```bash
# 确保有写入权限
chmod 755 VectorStore/
```

#### Q4：查询结果不包含质量评分
**A**：旧格式文件没有质量信息，可以重新存储或运行迁移脚本。

### 日志调试

启用详细日志：

```bash
# 设置环境变量
export KILO_MEMORY_DEBUG=true
export LOG_LEVEL=DEBUG

# 运行MCP
python kilo_memory_server_enhanced.py
```

日志文件位置：`logs/kilo_memory_enhanced.log`

## 性能考虑

### 内存使用

增强版增加了以下内存开销：
- 进化数据库连接：~5MB
- 质量评估缓存：~10MB（可配置）
- 关联分析矩阵：取决于记忆数量

建议系统要求：
- 内存：≥512MB
- 存储：额外100MB用于进化数据库
- CPU：现代处理器即可

### 响应时间

| 操作 | 原始MCP | 增强版MCP | 优化建议 |
|------|---------|-----------|----------|
| 存储记忆 | 10-50ms | 50-200ms | 批量存储 |
| 查询记忆 | 20-100ms | 30-150ms | 使用质量过滤减少结果集 |
| 进化操作 | N/A | 100-500ms | 异步执行 |
| 网络分析 | N/A | 1-5s | 定期缓存结果 |

### 优化建议

1. **定期清理**：删除低质量记忆
2. **批量操作**：使用批量API减少开销
3. **缓存配置**：调整缓存大小和TTL
4. **异步处理**：耗时的进化操作异步执行

## 回滚方案

如果遇到问题，可以回滚到原始MCP：

### 步骤1：停止增强版MCP

```bash
# 查找并终止进程
ps aux | grep kilo_memory_server_enhanced
kill <pid>
```

### 步骤2：恢复原始MCP

```bash
# 恢复原始文件
cp KiloMemoryMCP/kilo_memory_server.py ../Roo_Code/MCP/KiloMemoryMCP/

# 更新配置（如果需要）
```

### 步骤3：验证回滚

```bash
# 启动原始MCP
python ../Roo_Code/MCP/KiloMemoryMCP/kilo_memory_server.py

# 测试基本功能
store_kilo_memory("测试回滚", tags=["test"])
```

## 支持与反馈

### 获取帮助

1. **文档**：查看 `TECHNICAL_DOCUMENTATION.md`
2. **示例**：查看 `examples/` 目录
3. **问题**：提交到项目Issue跟踪器

### 报告问题

提供以下信息：
- MCP版本
- 错误日志
- 复现步骤
- 系统环境

### 贡献指南

欢迎贡献：
1. Fork仓库
2. 创建功能分支
3. 提交Pull Request
4. 通过测试

## 总结

增强版 KiloMemoryMCP 提供了显著的改进，同时保持了完全的向后兼容性。迁移过程简单安全，您可以逐步采用新功能，无需一次性改变现有工作流程。

主要优势：
- ✅ 完全向后兼容
- ✅ 渐进式采用
- ✅ 性能可控
- ✅ 丰富的监控和调试工具
- ✅ 活跃的开发和维护

开始迁移，体验更智能的记忆管理系统！

---

*迁移指南版本：v1.0.0*
*最后更新：2026-01-20*
*适用于：KiloMemoryMCP 增强版 v2.0.0*