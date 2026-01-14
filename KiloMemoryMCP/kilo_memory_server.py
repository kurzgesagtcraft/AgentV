import os
import json
import sqlite3
import datetime
import subprocess
import socket
import threading
import time
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP")

# 路径配置
PROJECT_ROOT = r"d:/vscode/AgentV"
MEMORY_DIR = os.path.join(PROJECT_ROOT, "dailynote", "KiloMemory")
DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "knowledge_base.sqlite")
VCP_PORT = 6005  # 默认 VCP 端口

def is_vcp_running(port: int) -> bool:
    """检查指定端口是否已被占用，或是否存在启动锁"""
    # 1. 检查端口
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', port)) == 0:
            return True
    
    # 2. 检查启动锁文件 (防止在端口绑定前的启动间隙重复启动)
    lock_file = os.path.join(PROJECT_ROOT, ".vcp_start.lock")
    if os.path.exists(lock_file):
        # 如果锁文件超过 30 秒，认为已失效
        if time.time() - os.path.getmtime(lock_file) < 30:
            return True
    return False

def start_vcp_backend():
    """在后台启动 VCP 后端"""
    if is_vcp_running(VCP_PORT):
        return

    lock_file = os.path.join(PROJECT_ROOT, ".vcp_start.lock")
    try:
        # 创建启动锁
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        
        # 使用 start_server.bat 启动
        # /min 最小化运行，减少干扰
        cmd = ["cmd", "/c", "start", "/min", "start_server.bat"]
        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # 启动后稍微等待，然后清理锁文件（VCP 此时应该已经开始绑定端口了）
        time.sleep(5)
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception:
        if os.path.exists(lock_file):
            os.remove(lock_file)

def ensure_memory_dir():
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)

def get_db_connection():
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 dailynote 文件夹。
    这些记忆会被项目的 KnowledgeBaseManager 自动扫描并建立向量索引。
    :param content: 记忆内容
    :param tags: 标签列表
    """
    try:
        ensure_memory_dir()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memory_{timestamp}.md"
        filepath = os.path.join(MEMORY_DIR, filename)
        
        # 构建 Markdown 内容，符合项目的 Tag 提取规则
        tag_str = ", ".join(tags) if tags else "KiloMemory"
        md_content = f"""# Kilo Memory - {datetime.datetime.now().isoformat()}

{content}

Tag: {tag_str}
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        return f"Successfully stored memory to file: {filepath}. It will be indexed by KnowledgeBaseManager shortly."
    except Exception as e:
        return f"Error storing memory: {str(e)}"

@mcp.tool()
def query_kilo_memory(query: str = "", limit: int = 10) -> str:
    """
    查询 Kilo Code 的记忆。
    优先从 SQLite 数据库中检索已索引的内容，如果数据库不可用则列出本地文件。
    :param query: 查询关键词 (模糊匹配内容)
    :param limit: 返回数量限制
    """
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            sql = """
                SELECT c.content, f.path, f.updated_at 
                FROM chunks c 
                JOIN files f ON c.file_id = f.id 
                WHERE f.diary_name = 'KiloMemory' 
                AND c.content LIKE ? 
                ORDER BY f.updated_at DESC 
                LIMIT ?
            """
            cursor.execute(sql, (f"%{query}%", limit))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "content": row['content'],
                    "source": row['path'],
                    "time": datetime.datetime.fromtimestamp(row['updated_at']).isoformat() if row['updated_at'] else "unknown"
                })
            conn.close()
            
            if results:
                return json.dumps(results, indent=2, ensure_ascii=False)
        
        ensure_memory_dir()
        files = [f for f in os.listdir(MEMORY_DIR) if f.endswith(".md")]
        files.sort(reverse=True)
        
        results = []
        for fname in files:
            if len(results) >= limit:
                break
            fpath = os.path.join(MEMORY_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                if query.lower() in content.lower():
                    results.append({
                        "file": fname,
                        "content": content[:500] + "..." if len(content) > 500 else content
                    })
        
        if not results:
            return "No matching memories found."
            
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error querying memory: {str(e)}"

@mcp.tool()
def list_all_kilo_memories(limit: int = 20) -> str:
    """
    列出最近的 Kilo Code 记忆。
    """
    return query_kilo_memory("", limit)

if __name__ == "__main__":
    # 启动时尝试静默启动 VCP 后端
    threading.Thread(target=start_vcp_backend, daemon=True).start()
    # 运行 MCP 服务器
    mcp.run()