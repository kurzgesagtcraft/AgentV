#!/usr/bin/env python3
"""
测试改进的query_kilo_memory功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入改进的回忆系统
    from KiloMemoryMCP.improved_recall_system import (
        ProactiveRecallEngine, 
        NaturalRecallIntegrator,
        setup_enhanced_recall_system
    )
    
    print("✅ 改进的回忆系统导入成功")
    
    # 模拟内存管理器
    class MockMemoryManager:
        def query_memories(self, query, limit, min_quality):
            # 模拟返回硬件环境相关的记忆
            if "硬件" in query or "系统" in query or "电脑" in query:
                return [
                    {
                        "content": "电脑硬件配置：ROG Strix G834JY，i9-13980HX处理器，RTX 4090显卡，64GB DDR5内存，2TB NVMe SSD",
                        "quality_score": 0.9,
                        "type": "fact",
                        "source": "memory_20260120_hardware.md",
                        "time": "2026-01-20T22:31:46"
                    },
                    {
                        "content": "系统配置：Windows 11专业版，ASUS ROG Strix笔记本，高性能游戏工作站",
                        "quality_score": 0.8,
                        "type": "fact",
                        "source": "memory_20260120_system.md",
                        "time": "2026-01-20T22:28:14"
                    }
                ]
            return []
    
    # 创建改进的回忆系统
    memory_manager = MockMemoryManager()
    recall_system = setup_enhanced_recall_system(memory_manager)
    recall_engine = recall_system["recall_engine"]
    recall_integrator = recall_system["integrator"]
    
    print("✅ 改进的回忆系统初始化成功")
    
    # 测试查询
    test_queries = [
        "电脑硬件环境",
        "系统配置",
        "回忆我的电脑配置",
        "Windows 11系统信息"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"测试查询: '{query}'")
        print(f"{'='*60}")
        
        # 检查是否应该触发回忆
        should_recall, recall_info = recall_engine.should_recall(query)
        
        if should_recall:
            print(f"✅ 触发主动回忆: {recall_info['triggers']}")
            print(f"   任务类型: {recall_info['context']['task_type']}")
            print(f"   关键概念: {recall_info['context']['concepts']}")
            
            # 执行回忆
            recall_results = recall_engine.execute_recall(recall_info["context"])
            
            if recall_results.get("success"):
                print(f"✅ 回忆执行成功")
                print(f"   构建的查询: {recall_results['query']}")
                print(f"   找到结果数: {len(recall_results['results'])}")
                
                # 自然集成
                natural_response = recall_integrator.integrate_recall(recall_results)
                if natural_response:
                    print(f"\n自然回忆回应:\n{natural_response}")
                
                # 显示详细结果
                print(f"\n详细结果:")
                for i, mem in enumerate(recall_results["results"], 1):
                    print(f"  {i}. 【{mem.get('type', 'unknown')}】")
                    print(f"     质量: {mem.get('quality_score', 0):.2f}")
                    print(f"     相关性: {mem.get('relevance_score', 0):.2f}")
                    print(f"     内容: {mem.get('content', '')[:80]}...")
            else:
                print(f"❌ 回忆执行失败: {recall_results.get('error', '未知错误')}")
        else:
            print(f"❌ 未触发主动回忆")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保improved_recall_system.py在正确的位置")
except Exception as e:
    print(f"❌ 测试过程中出现错误: {e}")
    import traceback
    traceback.print_exc()