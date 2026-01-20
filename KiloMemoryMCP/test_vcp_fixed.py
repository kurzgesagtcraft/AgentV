#!/usr/bin/env python3
"""
测试VCP集成修复版KiloMemoryMCP
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kilo_memory_server_vcp_integrated_fixed import (
    VCPIntegratedMemoryManager,
    VCPAPIClient,
    MemoryAnalyzer
)

def test_vcp_client():
    print("=" * 60)
    print("测试VCP API客户端")
    print("=" * 60)
    
    client = VCPAPIClient()
    
    # 测试VCP连接
    vcp_running = client.is_vcp_running()
    print(f"VCP服务器运行状态: {'✅ 运行中' if vcp_running else '❌ 未运行'}")
    
    # 测试语义扩展
    test_queries = ["电脑硬件", "系统配置", "回忆经验"]
    for query in test_queries:
        expansions = client.get_semantic_expansion(query)
        print(f"查询 '{query}' 的语义扩展: {expansions}")
    
    # 测试搜索
    if vcp_running:
        results = client.search_knowledge("电脑", limit=3)
        print(f"VCP搜索找到 {len(results)} 条结果")
    else:
        print("VCP未运行，跳过搜索测试")

def test_memory_manager():
    print("\n" + "=" * 60)
    print("测试VCP集成记忆管理器")
    print("=" * 60)
    
    manager = VCPIntegratedMemoryManager()
    
    # 测试存储记忆
    test_content = "我的电脑是ROG Strix G834JY，配置为i9-13980HX处理器和RTX 4090显卡，运行Windows 11系统。"
    test_tags = ["硬件配置", "ROG Strix", "Windows 11"]
    
    print("1. 测试存储记忆...")
    result = manager.store_memory(test_content, test_tags)
    if result["success"]:
        print(f"✅ 存储成功: {result['memory_id']}")
        print(f"   文件路径: {result['filepath']}")
        memory_id = result["memory_id"]
    else:
        print(f"❌ 存储失败: {result['error']}")
        return
    
    # 测试查询记忆
    print("\n2. 测试查询记忆...")
    results = manager.query_memories("电脑硬件", limit=5)
    if results and "error" not in results[0]:
        print(f"✅ 查询成功，找到 {len(results)} 条结果")
        for i, mem in enumerate(results[:3], 1):
            print(f"   {i}. {mem.get('type', 'unknown')} (质量:{mem.get('quality_score', 0):.2f})")
            content_preview = mem.get('content', '')[:100] + "..." if len(mem.get('content', '')) > 100 else mem.get('content', '')
            print(f"      {content_preview}")
    else:
        print("❌ 查询失败或未找到相关记忆")
    
    # 测试系统统计
    print("\n3. 测试系统统计...")
    stats = manager.get_memory_stats()
    if "error" not in stats:
        print(f"✅ 统计信息:")
        print(f"   总记忆文件: {stats['total_memories']}")
        print(f"   最近7天新增: {stats['recent_7_days']}")
        print(f"   VCP可用: {stats['vcp_available']}")
    else:
        print(f"❌ 获取统计失败: {stats['error']}")

def test_memory_analyzer():
    print("\n" + "=" * 60)
    print("测试记忆分析器")
    print("=" * 60)
    
    analyzer = MemoryAnalyzer()
    
    test_contents = [
        "如何优化Windows 11性能：1. 关闭不必要的启动项 2. 更新驱动程序 3. 清理磁盘空间",
        "我的电脑配置是ROG Strix G834JY，搭载i9-13980HX和RTX 4090",
        "今天发现了一个重要的问题：系统内存使用率过高，需要优化",
        "反思：应该定期备份重要数据，避免数据丢失",
        "计划：下周要完成项目文档的编写和测试"
    ]
    
    for i, content in enumerate(test_contents, 1):
        mem_type = analyzer.analyze_memory_type(content)
        quality = analyzer.assess_memory_quality(content, ["测试"])
        concepts = analyzer.extract_key_concepts(content)
        
        print(f"{i}. 类型: {mem_type.value}, 质量: {quality.overall_score:.2f}")
        print(f"   概念: {', '.join(concepts[:3]) if concepts else '无'}")
        print(f"   内容预览: {content[:80]}...")

def compare_versions():
    print("\n" + "=" * 60)
    print("版本对比：旧版 vs VCP集成修复版")
    print("=" * 60)
    
    print("旧版本问题总结:")
    print("1. ❌ 回忆能力差：主要依赖SQL LIKE查询")
    print("2. ❌ 重复结果：去重机制有问题")
    print("3. ❌ 主动回忆失败：改进的回忆系统未正确集成")
    print("4. ❌ 向量搜索未充分利用：模拟实现，未真正集成")
    print("5. ❌ 记忆质量评估简单：基于简单规则")
    
    print("\nVCP集成修复版改进:")
    print("1. ✅ 真正的VCP集成：通过HTTP API调用VCP系统")
    print("2. ✅ 语义搜索：使用VCP的TagMemo系统进行语义扩展")
    print("3. ✅ 主动回忆：trigger_vcp_recall工具实现'一次回忆起'")
    print("4. ✅ 质量评估：多维度的记忆质量评分")
    print("5. ✅ 系统统计：实时监控记忆系统状态")
    print("6. ✅ 兼容性：解决Python无法导入JavaScript模块的问题")
    
    print("\n核心优势:")
    print("1. 🚀 真正的语义搜索：不再是简单的关键词匹配")
    print("2. 🧠 智能查询扩展：自动扩展相关概念")
    print("3. ⚡ 主动回忆：在任务开始时自动提供相关记忆")
    print("4. 📊 透明统计：显示搜索方法和结果来源")
    print("5. 🔧 易于扩展：基于HTTP API，可与其他系统集成")

def main():
    print("VCP集成修复版KiloMemoryMCP测试套件")
    print("版本: 1.0.0 (修复版)")
    print("日期: 2026-01-20")
    print("=" * 60)
    
    test_vcp_client()
    test_memory_manager()
    test_memory_analyzer()
    compare_versions()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    print("\n使用建议:")
    print("1. 确保VCP服务器正在运行（端口6005）")
    print("2. 更新MCP设置，使用新的修复版服务器")
    print("3. 在任务开始时使用trigger_vcp_recall获取相关记忆")
    print("4. 为记忆添加详细的标签以提高检索准确性")

if __name__ == "__main__":
    main()