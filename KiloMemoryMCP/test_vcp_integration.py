"""
测试VCP集成版KiloMemoryMCP的功能
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入VCP集成版
from kilo_memory_server_vcp_integrated import (
    VCPIntegratedMemoryManager,
    store_kilo_memory,
    query_kilo_memory,
    trigger_vcp_recall,
    get_memory_stats
)

def test_memory_manager():
    """测试记忆管理器"""
    print("=" * 60)
    print("测试VCP集成记忆管理器")
    print("=" * 60)
    
    manager = VCPIntegratedMemoryManager()
    
    # 测试存储记忆
    print("\n1. 测试存储记忆...")
    test_content = "这是我的测试记忆内容，用于验证VCP集成版的功能。"
    test_tags = ["测试", "VCP集成", "验证"]
    
    result = manager.store_memory(test_content, test_tags)
    if result["success"]:
        print(f"✅ 存储成功: {result['memory_id']}")
        print(f"   文件路径: {result['filepath']}")
    else:
        print(f"❌ 存储失败: {result['error']}")
    
    # 测试查询记忆
    print("\n2. 测试查询记忆...")
    query = "测试 VCP"
    results = manager.query_memories_vcp(query, limit=5)
    
    if results and not ("error" in results[0]):
        print(f"✅ 找到 {len(results)} 条相关记忆:")
        for i, mem in enumerate(results[:3], 1):
            print(f"   {i}. 质量:{mem.get('quality_score', 0):.2f} | 方法:{mem.get('search_method', 'unknown')}")
            if "content" in mem:
                preview = mem["content"][:100] + "..." if len(mem["content"]) > 100 else mem["content"]
                print(f"      内容: {preview}")
    else:
        print("❌ 查询失败或未找到相关记忆")
    
    # 测试语义扩展
    print("\n3. 测试语义扩展...")
    test_queries = ["电脑硬件", "系统配置", "回忆经验"]
    
    for q in test_queries:
        expansions = manager._expand_query_with_tagmemo(q)
        print(f"  查询 '{q}' 的扩展: {expansions[:3]}...")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

def test_tool_functions():
    """测试工具函数"""
    print("\n" + "=" * 60)
    print("测试工具函数")
    print("=" * 60)
    
    # 测试query_kilo_memory工具
    print("\n1. 测试query_kilo_memory工具...")
    response = query_kilo_memory("电脑硬件", limit=3)
    print(f"响应长度: {len(response)} 字符")
    print(f"响应预览: {response[:200]}...")
    
    # 测试trigger_vcp_recall工具
    print("\n2. 测试trigger_vcp_recall工具...")
    user_message = "我想了解我的电脑硬件配置"
    recall_response = trigger_vcp_recall(user_message)
    if recall_response:
        print(f"主动回忆响应: {recall_response[:200]}...")
    else:
        print("未触发主动回忆")
    
    # 测试get_memory_stats工具
    print("\n3. 测试get_memory_stats工具...")
    stats_response = get_memory_stats()
    print(f"统计信息: {stats_response[:300]}...")
    
    print("\n" + "=" * 60)
    print("工具函数测试完成")
    print("=" * 60)

def compare_old_vs_new():
    """对比新旧版本"""
    print("\n" + "=" * 60)
    print("对比新旧版本KiloMemoryMCP")
    print("=" * 60)
    
    print("\n旧版本问题总结:")
    print("1. ❌ 回忆能力差：主要依赖SQL LIKE查询")
    print("2. ❌ 重复结果：去重机制有问题")
    print("3. ❌ 主动回忆失败：改进的回忆系统未正确集成")
    print("4. ❌ 向量搜索未充分利用：模拟实现，未真正集成")
    print("5. ❌ 记忆质量评估简单：基于简单规则")
    
    print("\n新版本改进:")
    print("1. ✅ 直接集成VCP向量搜索：使用KnowledgeBaseManager")
    print("2. ✅ 使用TagMemo语义扩展：实现真正的语义理解")
    print("3. ✅ 优化去重机制：基于内容哈希去重")
    print("4. ✅ 实现真正的'一次回忆起'：trigger_vcp_recall工具")
    print("5. ✅ 改进质量评估：结合向量相似度和内容结构")
    print("6. ✅ 提供搜索统计：显示VCP向量搜索和文件系统搜索的结果")
    
    print("\n核心优势:")
    print("1. 🚀 真正的语义搜索：不再是简单的关键词匹配")
    print("2. 🧠 智能查询扩展：自动扩展相关概念")
    print("3. ⚡ 主动回忆：在任务开始时自动提供相关记忆")
    print("4. 📊 透明统计：显示搜索方法和结果来源")
    print("5. 🔧 易于扩展：基于VCP生态系统，可与其他工具集成")
    
    print("\n" + "=" * 60)
    print("对比完成")
    print("=" * 60)

def main():
    """主测试函数"""
    print("VCP集成版KiloMemoryMCP测试套件")
    print("版本: 1.0.0")
    print("日期: 2026-01-20")
    print()
    
    # 运行测试
    test_memory_manager()
    test_tool_functions()
    compare_old_vs_new()
    
    print("\n✅ 所有测试完成！")
    print("\n使用建议:")
    print("1. 更新MCP设置，使用新的VCP集成版服务器")
    print("2. 在任务开始时使用trigger_vcp_recall获取相关记忆")
    print("3. 为记忆添加详细的标签以提高检索准确性")
    print("4. 定期使用get_memory_stats检查系统状态")

if __name__ == "__main__":
    main()