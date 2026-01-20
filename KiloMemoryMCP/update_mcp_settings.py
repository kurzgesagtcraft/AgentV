#!/usr/bin/env python3
"""
更新MCP设置，将KiloMemoryMCP指向新的VCP集成修复版
"""

import json
import os
import sys

# MCP设置文件路径
MCP_SETTINGS_PATH = r"c:/Users/kurzcraft/AppData/Roaming/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json"

# 备份文件路径
BACKUP_PATH = MCP_SETTINGS_PATH + ".backup"

def backup_original_settings():
    """备份原始设置文件"""
    if os.path.exists(MCP_SETTINGS_PATH):
        try:
            with open(MCP_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            print(f"✅ 原始设置已备份到: {BACKUP_PATH}")
            return True
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False
    else:
        print(f"❌ 设置文件不存在: {MCP_SETTINGS_PATH}")
        return False

def update_mcp_settings():
    """更新MCP设置"""
    try:
        # 读取当前设置
        with open(MCP_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        print("📋 当前KiloMemoryMCP配置:")
        current_config = settings.get("mcpServers", {}).get("KiloMemoryMCP", {})
        print(f"   命令: {current_config.get('command', 'N/A')}")
        print(f"   参数: {current_config.get('args', [])}")
        print(f"   描述: {current_config.get('description', 'N/A')}")
        
        # 更新配置
        new_config = {
            "command": "python",
            "args": ["D:/vscode/AgentV/KiloMemoryMCP/kilo_memory_server_vcp_integrated_fixed.py"],
            "alwaysAllow": [
                "store_kilo_memory",
                "query_kilo_memory", 
                "trigger_vcp_recall",
                "list_all_kilo_memories",
                "get_memory_stats"
            ],
            "disabled": False,
            "autoStart": True,
            "description": "Kilo Code VCP集成修复版记忆系统 - 支持真正的语义搜索和主动回忆"
        }
        
        # 更新设置
        settings["mcpServers"]["KiloMemoryMCP"] = new_config
        
        # 写回文件
        with open(MCP_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        print("\n✅ MCP设置已更新!")
        print("\n📋 新的KiloMemoryMCP配置:")
        print(f"   命令: {new_config['command']}")
        print(f"   参数: {new_config['args']}")
        print(f"   工具: {', '.join(new_config['alwaysAllow'][:3])}...")
        print(f"   描述: {new_config['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False

def verify_update():
    """验证更新是否成功"""
    try:
        with open(MCP_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        config = settings.get("mcpServers", {}).get("KiloMemoryMCP", {})
        
        # 检查关键字段
        expected_args = ["D:/vscode/AgentV/KiloMemoryMCP/kilo_memory_server_vcp_integrated_fixed.py"]
        actual_args = config.get("args", [])
        
        if actual_args == expected_args:
            print("\n✅ 验证通过: MCP设置已正确更新")
            print(f"   使用的服务器: {actual_args[0]}")
            
            # 检查工具列表
            tools = config.get("alwaysAllow", [])
            required_tools = ["store_kilo_memory", "query_kilo_memory", "trigger_vcp_recall"]
            missing_tools = [t for t in required_tools if t not in tools]
            
            if not missing_tools:
                print(f"   可用工具: {len(tools)} 个")
                return True
            else:
                print(f"⚠️ 缺少工具: {missing_tools}")
                return False
        else:
            print(f"❌ 验证失败: 参数不匹配")
            print(f"   期望: {expected_args}")
            print(f"   实际: {actual_args}")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def restore_backup():
    """从备份恢复设置"""
    if os.path.exists(BACKUP_PATH):
        try:
            with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            
            with open(MCP_SETTINGS_PATH, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            print(f"✅ 设置已从备份恢复: {BACKUP_PATH}")
            return True
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return False
    else:
        print(f"❌ 备份文件不存在: {BACKUP_PATH}")
        return False

def main():
    print("=" * 60)
    print("KiloMemoryMCP MCP设置更新工具")
    print("版本: 1.0.0")
    print("=" * 60)
    print("\n目标: 将KiloMemoryMCP更新为VCP集成修复版")
    print("改进:")
    print("  ✅ 真正的VCP集成 (通过HTTP API)")
    print("  ✅ 语义搜索 (TagMemo系统)")
    print("  ✅ 主动回忆 (trigger_vcp_recall)")
    print("  ✅ 解决Python无法导入JavaScript模块的问题")
    print("=" * 60)
    
    # 步骤1: 备份
    print("\n步骤1: 备份原始设置...")
    if not backup_original_settings():
        print("❌ 无法继续，备份失败")
        return
    
    # 步骤2: 更新
    print("\n步骤2: 更新MCP设置...")
    if not update_mcp_settings():
        print("❌ 更新失败")
        return
    
    # 步骤3: 验证
    print("\n步骤3: 验证更新...")
    if not verify_update():
        print("\n⚠️ 验证失败，正在恢复备份...")
        restore_backup()
        return
    
    # 步骤4: 使用说明
    print("\n" + "=" * 60)
    print("更新完成！")
    print("=" * 60)
    
    print("\n📋 下一步操作:")
    print("1. 重启VSCode，或")
    print("2. 使用命令面板执行 'Kilo Code: Reload MCP Servers'")
    print("3. 确保VCP服务器正在运行: cd d:/vscode/AgentV && start_server.bat")
    
    print("\n🔧 测试新功能:")
    print("1. 存储记忆: store_kilo_memory('内容', ['标签'])")
    print("2. 查询记忆: query_kilo_memory('关键词', limit=5)")
    print("3. 主动回忆: trigger_vcp_recall('任务描述')")
    print("4. 查看统计: get_memory_stats()")
    
    print("\n⚠️ 如果需要恢复原始设置，运行:")
    print(f"   python {__file__} --restore")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        print("恢复原始设置...")
        if restore_backup():
            print("✅ 恢复成功")
        else:
            print("❌ 恢复失败")
    else:
        main()