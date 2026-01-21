#!/usr/bin/env python3
"""
测试KiloMemoryMCP修复后的连接
"""

import requests
import json

VCP_API_URL = "http://localhost:6005"
VCP_API_KEY = "vcp123456"

def test_connection():
    """测试VCP API连接"""
    print("🔍 测试VCP API连接...")
    
    # 测试1: 不带认证头
    print("\n1. 测试不带认证头:")
    try:
        response = requests.get(f"{VCP_API_URL}/api/health", timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ 预期结果: 401 Unauthorized (需要认证)")
        else:
            print(f"   ❌ 意外状态码: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
    
    # 测试2: 带认证头
    print("\n2. 测试带认证头:")
    try:
        headers = {"Authorization": f"Bearer {VCP_API_KEY}"}
        response = requests.get(f"{VCP_API_URL}/api/health", headers=headers, timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 连接成功!")
            data = response.json()
            print(f"   响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"   ❌ 认证失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
    
    # 测试3: 测试搜索API
    print("\n3. 测试搜索API:")
    try:
        headers = {"Authorization": f"Bearer {VCP_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "query": "电脑硬件配置",
            "limit": 3,
            "tagBoost": 0.5,
            "minScore": 0.3,
            "includeTags": True
        }
        response = requests.post(f"{VCP_API_URL}/api/search", headers=headers, json=payload, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                print(f"   ✅ 搜索成功!")
                print(f"   找到 {len(data.get('results', []))} 个结果")
                for i, result in enumerate(data.get('results', [])[:2]):
                    print(f"   结果{i+1}: {result.get('text', '')[:100]}...")
            else:
                print(f"   ⚠️ API返回失败: {data.get('error', '未知错误')}")
        else:
            print(f"   ❌ 搜索失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
    
    # 测试4: 测试主动回忆API
    print("\n4. 测试主动回忆API:")
    try:
        headers = {"Authorization": f"Bearer {VCP_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "context": "修复KiloMemoryMCP连接问题",
            "maxMemories": 3,
            "relevanceThreshold": 0.3
        }
        response = requests.post(f"{VCP_API_URL}/api/recall/trigger", headers=headers, json=payload, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                print(f"   ✅ 主动回忆成功!")
                print(f"   找到 {len(data.get('memories', []))} 个相关记忆")
            else:
                print(f"   ⚠️ API返回失败: {data.get('error', '未知错误')}")
        else:
            print(f"   ❌ 主动回忆失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 主动回忆失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("KiloMemoryMCP连接修复测试")
    print("=" * 60)
    test_connection()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)