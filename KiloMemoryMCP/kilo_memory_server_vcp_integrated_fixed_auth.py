"""
VCP集成版KiloMemoryMCP服务器（修复版+认证修复）
解决Python无法直接导入JavaScript模块的问题，通过HTTP API调用VCP系统
修复认证问题：添加Bearer token认证头
"""

import os
import sys
import json
import sqlite3
import datetime
import hashlib
import re
import requests
import subprocess
import time
import threading
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from mcp.server.fastmcp import FastMCP

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 路径配置
PROJECT_ROOT = r"d:/vscode/AgentV"
MEMORY_DIR = os.path.join(PROJECT_ROOT, "dailynote", "KiloMemory")
DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "knowledge_base.sqlite")
EVOLUTION_DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "memory_evolution.sqlite")

# VCP API配置
VCP_API_URL = "http://localhost:6005"  # VCP服务器地址
VCP_API_TIMEOUT = 10  # 秒
VCP_API_KEY = "vcp123456"  # 从config.env读取的Key

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_VCP_Integrated_Fixed_Auth")

# 记忆类型枚举
class MemoryType(Enum):
    FACT = "fact"
    EXPERIENCE = "experience"
    SKILL = "skill"
    INSIGHT = "insight"
    REFLECTION = "reflection"
    PLAN = "plan"

# 记忆质量评分
@dataclass
class MemoryQuality:
    relevance: float = 0.0
    clarity: float = 0.0
    completeness: float = 0.0
    importance: float = 0.0
    novelty: float = 0.0
    
    @property
    def overall_score(self) -> float:
        weights = {
            'relevance': 0.25,
            'clarity': 0.20,
            'completeness': 0.15,
            'importance': 0.25,
            'novelty': 0.15
        }
        return sum(getattr(self, attr) * weight for attr, weight in weights.items())

# VCP API客户端（修复认证问题）
class VCPAPIClient:
    def __init__(self, base_url: str = VCP_API_URL, api_key: str = VCP_API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.timeout = VCP_API_TIMEOUT
        # 设置默认的Authorization头
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def is_vcp_running(self) -> bool:
        """检查VCP服务器是否运行"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """通过VCP API搜索知识库"""
        try:
            # 调用真正的VCP向量搜索API
            return self._real_vcp_search(query, limit)
        except Exception as e:
            sys.stderr.write(f"VCP搜索失败: {e}\n")
            sys.stderr.flush()
            # 回退到模拟搜索
            return self._simulate_vcp_search(query, limit)
    
    def _real_vcp_search(self, query: str, limit: int) -> List[Dict]:
        """真正的VCP向量搜索"""
        try:
            # 调用向量搜索API
            response = self.session.post(
                f"{self.base_url}/api/search",
                json={
                    "query": query,
                    "limit": limit,
                    "tagBoost": 0.5,  # 使用TagMemo增强
                    "minScore": 0.3,  # 最小相似度分数
                    "includeTags": True
                },
                timeout=VCP_API_TIMEOUT
            )
            
            if response.status_code != 200:
                print(f"VCP API返回错误: {response.status_code}")
                return []
            
            data = response.json()
            if not data.get("success", False):
                print(f"VCP API返回失败: {data.get('error', '未知错误')}")
                return []
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "text": item.get("text", ""),
                    "sourceFile": item.get("sourceFile", ""),
                    "score": item.get("score", 0.0),
                    "diary_name": item.get("sourceFile", "").split("/")[-2] if "/" in item.get("sourceFile", "") else "VCP知识库",
                    "matchedTags": item.get("matchedTags", []),
                    "boostFactor": item.get("boostFactor", 0),
                    "tagMatchScore": item.get("tagMatchScore", 0),
                    "tagMatchCount": item.get("tagMatchCount", 0)
                })
            
            return results
            
        except Exception as e:
            print(f"调用VCP向量搜索API失败: {e}")
            return []
    
    def _simulate_vcp_search(self, query: str, limit: int) -> List[Dict]:
        """模拟VCP搜索（回退方案）"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.content as text, f.path as sourceFile, f.updated_at, f.diary_name
                FROM chunks c 
                JOIN files f ON c.file_id = f.id 
                WHERE c.content LIKE ? 
                ORDER BY f.updated_at DESC 
                LIMIT ?
            """, (f"%{query}%", limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "text": row['text'],
                    "sourceFile": row['sourceFile'],
                    "score": 0.8,  # 模拟相似度分数
                    "diary_name": row['diary_name']
                })
            
            conn.close()
            return results
        except Exception as e:
            print(f"模拟VCP搜索失败: {e}")
            return []
    
    def trigger_vcp_recall(self, context: str, max_memories: int = 5) -> Dict:
        """触发主动回忆"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/recall/trigger",
                json={
                    "context": context,
                    "maxMemories": max_memories,
                    "relevanceThreshold": 0.3
                },
                timeout=VCP_API_TIMEOUT
            )
            
            if response.status_code != 200:
                print(f"主动回忆API返回错误: {response.status_code}")
                return {"success": False, "error": f"API错误: {response.status_code}"}
            
            data = response.json()
            if not data.get("success", False):
                return {"success": False, "error": data.get("error", "未知错误")}
            
            return {
                "success": True,
                "context": context,
                "memories": data.get("memories", []),
                "summary": data.get("summary", ""),
                "stats": data.get("stats", {})
            }
            
        except Exception as e:
            print(f"触发主动回忆失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_semantic_expansion(self, query: str) -> List[str]:
        """获取语义扩展查询词"""
        try:
            # 尝试调用VCP的标签搜索API
            response = self.session.post(
                f"{self.base_url}/api/search/tags",
                json={"query": query, "limit": 5},
                timeout=VCP_API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    expansions = [query]
                    for tag_result in data.get("results", []):
                        tag = tag_result.get("tag", "")
                        if tag and tag not in expansions:
                            expansions.append(tag)
                            expansions.append(f"{query} {tag}")
                    return expansions[:5]
        except:
            pass
        
        # 回退到基于常见概念的语义扩展
        expansions = [query]
        
        hardware_concepts = {
            "电脑": ["计算机", "PC", "笔记本", "台式机", "工作站"],
            "硬件": ["配置", "规格", "参数", "设备", "组件"],
            "环境": ["系统", "设置", "配置", "信息", "详情"],
            "配置": ["规格", "参数", "性能", "硬件", "系统"],
            "系统": ["操作系统", "Windows", "软件", "平台", "环境"],
            "回忆": ["记忆", "经验", "记录", "历史", "过去"],
            "查询": ["搜索", "查找", "检索", "寻找", "探索"]
        }
        
        for original, synonyms in hardware_concepts.items():
            if original in query:
                for synonym in synonyms:
                    expanded = query.replace(original, synonym)
                    expansions.append(expanded)
                    expansions.append(f"{query} {synonym}")
        
        return list(set(expansions))[:5]
    
    def start_vcp_service(self) -> bool:
        """启动VCP服务（无窗口版本）"""
        try:
            # 使用 sys.stderr 输出，确保在 MCP 环境中可见
            sys.stderr.write("🚀 正在尝试启动VCP服务...\n")
            sys.stderr.flush()
            
            # 检查VCP服务器是否已经在运行
            if self.is_vcp_running():
                sys.stderr.write("✅ VCP服务已经在运行\n")
                sys.stderr.flush()
                return True
            
            # 查找VCP服务器启动脚本
            vcp_server_paths = [
                os.path.join(PROJECT_ROOT, "server.js"),
                os.path.join(PROJECT_ROOT, "start_server.bat"),
                os.path.join(PROJECT_ROOT, "start_all_services.bat")
            ]
            
            server_script = None
            for path in vcp_server_paths:
                if os.path.exists(path):
                    server_script = path
                    break
            
            if not server_script:
                sys.stderr.write("❌ 未找到VCP服务器启动脚本\n")
                sys.stderr.flush()
                return False
            
            sys.stderr.write(f"📁 找到VCP服务器脚本: {server_script}\n")
            sys.stderr.flush()
            
            # 根据脚本类型启动服务
            if server_script.endswith(".js"):
                # Node.js服务器 - 使用 start 命令在后台无窗口运行
                if sys.platform == "win32":
                    cmd = ["cmd", "/c", "start", "/B", "node", server_script]
                else:
                    cmd = ["node", server_script]
            elif server_script.endswith(".bat"):
                # Windows批处理脚本 - 使用 start 命令在后台无窗口运行
                if sys.platform == "win32":
                    cmd = ["cmd", "/c", "start", "/B", server_script]
                else:
                    cmd = [server_script]
            else:
                sys.stderr.write(f"❌ 不支持的脚本类型: {server_script}\n")
                sys.stderr.flush()
                return False
            
            # 在后台启动服务（无窗口）
            try:
                # 使用 subprocess 启动服务，不创建新控制台窗口
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                process = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    startupinfo=startupinfo
                )
                
                sys.stderr.write(f"✅ VCP服务启动中 (PID: {process.pid})...\n")
                sys.stderr.flush()
                
                # 等待服务启动
                for i in range(30):  # 最多等待30秒
                    time.sleep(1)
                    if self.is_vcp_running():
                        sys.stderr.write("✅ VCP服务启动成功！\n")
                        sys.stderr.flush()
                        return True
                    if i % 5 == 0:
                        sys.stderr.write(f"⏳ 等待VCP服务启动... ({i+1}/30秒)\n")
                        sys.stderr.flush()
                
                sys.stderr.write("⚠️ VCP服务启动超时，可能仍在启动中\n")
                sys.stderr.flush()
                return False
                
            except Exception as e:
                sys.stderr.write(f"❌ 启动VCP服务失败: {e}\n")
                sys.stderr.flush()
                return False
                
        except Exception as e:
            sys.stderr.write(f"❌ 启动VCP服务时发生错误: {e}\n")
            sys.stderr.flush()
            return False
    
    def ensure_vcp_service(self) -> bool:
        """确保VCP服务运行，如果未运行则自动启动"""
        if self.is_vcp_running():
            return True
        
        print("🔧 VCP服务未运行，尝试自动启动...")
        return self.start_vcp_service()

# 记忆分析器
class MemoryAnalyzer:
    def __init__(self):
        self.keyword_patterns = {
            'skill': r'(如何|步骤|方法|技巧|技能|操作)',
            'fact': r'(是|有|包含|包括|属于)',
            'experience': r'(经历|体验|感受|体会)',
            'insight': r'(发现|领悟|理解|认识到)',
            'reflection': r'(反思|总结|回顾|思考)',
            'plan': r'(计划|打算|目标|安排)'
        }
    
    def analyze_memory_type(self, content: str) -> MemoryType:
        content_lower = content.lower()
        type_scores = {mem_type: 0 for mem_type in MemoryType}
        
        for mem_type, pattern in self.keyword_patterns.items():
            matches = re.findall(pattern, content_lower)
            type_scores[MemoryType(mem_type)] = len(matches)
        
        if re.search(r'\d+\.\s|\-\s|\*\s', content):
            type_scores[MemoryType.SKILL] += 2
        if re.search(r'应该|建议|最好', content):
            type_scores[MemoryType.INSIGHT] += 1
        
        return max(type_scores.items(), key=lambda x: x[1])[0]
    
    def assess_memory_quality(self, content: str, tags: List[str]) -> MemoryQuality:
        quality = MemoryQuality()
        
        if tags:
            quality.relevance = min(1.0, len(tags) / 10)
        
        sentences = re.split(r'[。！？.!?]', content)
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        
        if 10 <= avg_sentence_length <= 50:
            quality.clarity = 0.8
        elif avg_sentence_length < 10:
            quality.clarity = 0.5
        else:
            quality.clarity = 0.6
        
        content_length = len(content)
        if content_length > 500:
            quality.completeness = 0.9
        elif content_length > 200:
            quality.completeness = 0.7
        elif content_length > 50:
            quality.completeness = 0.5
        else:
            quality.completeness = 0.3
        
        important_keywords = ['重要', '关键', '核心', '必须', '必要', 'essential', 'critical']
        has_important = any(keyword in content for keyword in important_keywords)
        quality.importance = 0.8 if has_important else 0.5
        
        quality.novelty = 0.7
        
        return quality
    
    def extract_key_concepts(self, content: str) -> List[str]:
        concepts = []
        concepts.extend(re.findall(r'【(.*?)】|\((.*?)\)|（(.*?)）', content))
        concepts.extend(re.findall(r'["\'](.*?)["\']', content))
        concepts.extend(re.findall(r'\b[A-Z][a-z]+\b', content))
        concepts = [c for sublist in concepts for c in sublist if c]
        concepts = list(set(concepts))
        return concepts

# 主记忆管理器（使用VCP API）
class VCPIntegratedMemoryManager:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.db_path = DB_PATH
        self.vcp_client = VCPAPIClient()
        self.analyzer = MemoryAnalyzer()
        self._ensure_directories()
    
    def _ensure_directories(self):
        os.makedirs(self.memory_dir, exist_ok=True)
    
    def generate_memory_id(self, content: str) -> str:
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
        timestamp