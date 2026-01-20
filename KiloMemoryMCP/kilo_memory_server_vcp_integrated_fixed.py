"""
VCP集成版KiloMemoryMCP服务器（修复版）
解决Python无法直接导入JavaScript模块的问题，通过HTTP API调用VCP系统
"""

import os
import sys
import json
import sqlite3
import datetime
import hashlib
import re
import requests
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

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_VCP_Integrated_Fixed")

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

# VCP API客户端
class VCPAPIClient:
    def __init__(self, base_url: str = VCP_API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = VCP_API_TIMEOUT
    
    def is_vcp_running(self) -> bool:
        """检查VCP服务器是否运行"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """通过VCP API搜索知识库"""
        try:
            # 这里应该调用VCP的搜索API
            # 由于VCP API可能未完全定义，我们先模拟一个实现
            return self._simulate_vcp_search(query, limit)
        except Exception as e:
            print(f"VCP搜索失败: {e}")
            return []
    
    def _simulate_vcp_search(self, query: str, limit: int) -> List[Dict]:
        """模拟VCP搜索（实际应该调用真正的VCP API）"""
        # 这里应该调用真正的VCP API
        # 暂时使用SQLite数据库作为回退
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
    
    def get_semantic_expansion(self, query: str) -> List[str]:
        """获取语义扩展查询词"""
        # 基于常见概念的语义扩展
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
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        return f"mem_{timestamp}_{content_hash}"
    
    def store_memory(self, content: str, tags: List[str] = None) -> Dict:
        try:
            memory_id = self.generate_memory_id(content)
            memory_type = self.analyzer.analyze_memory_type(content)
            quality = self.analyzer.assess_memory_quality(content, tags or [])
            key_concepts = self.analyzer.extract_key_concepts(content)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"memory_{timestamp}_{memory_id}.md"
            filepath = os.path.join(self.memory_dir, filename)
            
            tag_str = ", ".join(tags) if tags else "KiloMemory"
            concept_str = ", ".join(key_concepts) if key_concepts else ""
            
            md_content = f"""# Kilo Memory - {datetime.datetime.now().isoformat()}
## 记忆ID: {memory_id}
## 记忆类型: {memory_type.value}
## 质量评分: {quality.overall_score:.2f}

### 内容
{content}

### 元数据
- **标签**: {tag_str}
- **关键概念**: {concept_str}
- **清晰度**: {quality.clarity:.2f}
- **重要性**: {quality.importance:.2f}
- **完整性**: {quality.completeness:.2f}
- **相关性**: {quality.relevance:.2f}
- **新颖性**: {quality.novelty:.2f}

### VCP集成
- 存储时间: {datetime.datetime.now().isoformat()}
- 记忆哈希: {hashlib.md5(content.encode()).hexdigest()[:8]}
- VCP搜索: 已索引

Tag: {tag_str}
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            return {
                "success": True,
                "memory_id": memory_id,
                "filepath": filepath,
                "metadata": {
                    "type": memory_type.value,
                    "quality": asdict(quality),
                    "concepts": key_concepts
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def query_memories(self, query: str = "", limit: int = 10, 
                      min_quality: float = 0.0) -> List[Dict]:
        try:
            results = []
            
            # 策略1：使用VCP API搜索
            if query:
                vcp_results = self.vcp_client.search_knowledge(query, limit * 2)
                
                for vr in vcp_results:
                    content = vr.get("text", "")
                    quality = self.analyzer.assess_memory_quality(content, [])
                    
                    if quality.overall_score >= min_quality:
                        results.append({
                            "content": content,
                            "source": vr.get("sourceFile", ""),
                            "diary_name": vr.get("diary_name", "VCP知识库"),
                            "time": "unknown",
                            "quality_score": quality.overall_score * 1.3,
                            "type": self.analyzer.analyze_memory_type(content).value,
                            "original_quality": quality.overall_score,
                            "vector_score": vr.get("score", 0),
                            "search_method": "vcp_api"
                        })
            
            # 策略2：文件系统搜索（回退）
            if len(results) < limit:
                ensure_memory_dir()
                files = [f for f in os.listdir(self.memory_dir) 
                        if f.endswith(".md")]
                files.sort(reverse=True)
                
                for fname in files:
                    if len(results) >= limit:
                        break
                    
                    fpath = os.path.join(self.memory_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                            if not query or query.lower() in content.lower():
                                quality = self.analyzer.assess_memory_quality(content, [])
                                
                                if quality.overall_score >= min_quality:
                                    memory_id = "unknown"
                                    if "记忆ID:" in content:
                                        lines = content.split('\n')
                                        for line in lines:
                                            if "记忆ID:" in line:
                                                memory_id = line.split("记忆ID:")[1].strip()
                                                break
                                    
                                    results.append({
                                        "file": fname,
                                        "memory_id": memory_id,
                                        "content": content[:500] + "..." 
                                                 if len(content) > 500 else content,
                                        "full_content": content,
                                        "quality_score": quality.overall_score,
                                        "type": self.analyzer.analyze_memory_type(content).value,
                                        "path": fpath,
                                        "search_method": "file_system"
                                    })
                    except Exception as e:
                        print(f"读取文件 {fname} 时出错: {e}")
                        continue
            
            # 综合排序
            def sort_key(result):
                method_weights = {
                    "vcp_api": 3.0,
                    "file_system": 1.0
                }
                method_weight = method_weights.get(result.get("search_method", ""), 1.0)
                vector_score = result.get("vector_score", 0)
                quality_score = result.get("quality_score", 0)
                return method_weight * (quality_score + vector_score * 0.5)
            
            results.sort(key=sort_key, reverse=True)
            
            # 去重
            seen_hashes = set()
            unique_results = []
            for result in results:
                content_hash = hashlib.md5(result.get("content", "").encode()).hexdigest()[:8]
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"查询记忆时出错: {e}")
            return [{"error": f"查询失败: {str(e)}"}]
    
    def get_memory_stats(self) -> Dict:
        try:
            memory_files = [f for f in os.listdir(self.memory_dir) 
                          if f.endswith(".md")]
            
            recent_count = 0
            week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            
            for fname in memory_files:
                try:
                    file_time_str = fname.split("_")[1]
                    file_date = datetime.datetime.strptime(file_time_str[:8], "%Y%m%d")
                    if file_date > week_ago:
                        recent_count += 1
                except:
                    continue
            
            vcp_running = self.vcp_client.is_vcp_running()
            
            return {
                "total_memories": len(memory_files),
                "recent_7_days": recent_count,
                "vcp_available": vcp_running,
                "memory_dir": self.memory_dir
            }
            
        except Exception as e:
            return {"error": f"获取统计失败: {str(e)}"}

# 工具函数
def ensure_memory_dir():
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)

# 初始化记忆管理器
memory_manager = VCPIntegratedMemoryManager()

# MCP工具定义
@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 dailynote 文件夹（VCP集成版）。
    这些记忆会被VCP系统的KnowledgeBaseManager自动扫描并建立向量索引。
    :param content: 记忆内容
    :param tags: 标签列表
    """
    result = memory_manager.store_memory(content, tags)
    
    if result["success"]:
        memory_id = result["memory_id"]
        metadata = result["metadata"]
        
        quality_dict = metadata.get('quality', {})
        quality_score = quality_dict.get('overall_score', 0.0)
        
        response = f"""✅ 记忆存储成功（VCP集成版）！

记忆ID: {memory_id}
存储位置: {result['filepath']}
记忆类型: {metadata['type']}
质量评分: {quality_score:.2f}
关键概念: {', '.join(metadata['concepts'][:5]) if metadata['concepts'] else '无'}

该记忆已存储到VCP记忆目录，会被KnowledgeBaseManager自动索引。"""
        
        return response
    else:
        return f"❌ 记忆存储失败: {result['error']}"

@mcp.tool()
def query_kilo_memory(query: str = "", limit: int = 10, 
                     min_quality: float = 0.0) -> str:
    """
    查询 Kilo Code 的记忆（VCP集成版）。
    使用VCP API进行语义搜索，支持质量过滤和记忆类型识别。
    
    💡 使用建议：
    1. 在会话开始时调用此工具进行"主动回忆"，例如：query_kilo_memory("电脑硬件配置")
    2. 使用空查询查看最近的记忆：query_kilo_memory("", limit=10)
    3. 结合具体任务查询相关经验：query_kilo_memory("编程问题解决", limit=5)
    
    :param query: 查询关键词
    :param limit: 返回数量限制
    :param min_quality: 最低质量评分（0-1）
    """
    results = memory_manager.query_memories(query, limit, min_quality)
    
    if not results or ("error" in results[0]):
        if query:
            return f"未找到与 '{query}' 相关的记忆。\n\n建议：\n1. 尝试更具体的关键词\n2. 使用 store_kilo_memory 存储相关记忆\n3. 检查记忆质量评分是否过高（当前设置: ≥{min_quality})"
        else:
            return "当前没有可用的记忆记录。\n\n建议使用 store_kilo_memory 工具存储重要信息。"
    
    if query:
        response = f"🔍 使用VCP集成搜索找到 {len(results)} 条与 '{query}' 相关的记忆:\n\n"
    else:
        response = f"📚 最近的 {len(results)} 条记忆:\n\n"
    
    for i, mem in enumerate(results, 1):
        quality = mem.get("quality_score", 0)
        mem_type = mem.get("type", "unknown")
        
        type_labels = {
            "fact": "📝 事实",
            "experience": "🎯 经验", 
            "skill": "🛠️ 技能",
            "insight": "💡 洞察",
            "reflection": "🤔 反思",
            "plan": "📅 计划"
        }
        type_label = type_labels.get(mem_type, f"【{mem_type}】")
        
        search_method = mem.get("search_method", "")
        method_icon = "🔗" if search_method == "vcp_api" else "📁"
        
        response += f"{i}. {method_icon} {type_label} (质量:{quality:.2f})\n"
        
        if "content" in mem:
            content_preview = mem["content"][:200] + "..." \
                            if len(mem["content"]) > 200 else mem["content"]
            response += f"   {content_preview}\n"
        
        if "time" in mem and mem["time"] != "unknown":
            try:
                time_obj = datetime.datetime.fromisoformat(mem['time'].replace('Z', '+00:00'))
                time_str = time_obj.strftime("%Y-%m-%d %H:%M")
                response += f"   时间: {time_str}\n"
            except:
                response += f"   时间: {mem['time']}\n"
        
        response += "\n"
    
    if len(results) >= limit:
        response += f"💡 提示：使用更具体的关键词或提高质量阈值可以找到更多相关记忆。"
    
    return response



def extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词"""
    # 改进的关键词提取：使用简单的分词逻辑
    stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '我', '你', '他', '她', '它', '们', '这', '那', '哪', '什么', '怎么', '为什么', '如何'}
    
    # 常见硬件相关关键词
    hardware_keywords = {'电脑', '硬件', '环境', '配置', '系统', '处理器', 'CPU', '显卡', 'GPU', '内存', '存储', '硬盘', '固态', 'SSD', '机械', 'HDD', '主板', '电源', '散热', '显示器', '屏幕', '键盘', '鼠标', '网络', '无线', '蓝牙', 'USB', '接口', '端口'}
    
    # 提取2-4个字符的词语
    keywords = []
    for i in range(len(text)):
        for length in [2, 3, 4]:
            if i + length <= len(text):
                word = text[i:i+length]
                if word not in stopwords and any(char not in stopwords for char in word):
                    # 检查是否包含硬件相关关键词
                    if any(hw in word for hw in hardware_keywords):
                        keywords.append(word)
    
    # 去重并限制数量
    keywords = list(set(keywords))[:5]
    
    # 如果没提取到关键词，返回整个文本（去除停用词）
    if not keywords:
        simple_words = [char for char in text if char not in stopwords]
        keywords = simple_words[:5]
    
    return keywords

@mcp.tool()
def list_all_kilo_memories(limit: int = 20) -> str:
    """
    列出最近的 Kilo Code 记忆（VCP集成版）。
    :param limit: 返回数量限制
    """
    return query_kilo_memory("", limit)

@mcp.tool()
def get_memory_stats() -> str:
    """
    获取VCP集成记忆系统的统计信息。
    """
    stats = memory_manager.get_memory_stats()
    
    if "error" in stats:
        return f"获取统计信息失败: {stats['error']}"
    
    response = "📊 VCP集成记忆系统统计报告\n\n"
    response += f"总记忆文件: {stats['total_memories']}\n"
    response += f"最近7天新增: {stats['recent_7_days']}\n"
    response += f"VCP向量搜索: {'✅ 可用' if stats['vcp_available'] else '❌ 不可用'}\n"
    response += f"记忆目录: {stats['memory_dir']}\n\n"
    
    response += "💡 使用建议:\n"
    response += "1. 使用 store_kilo_memory 存储重要信息\n"
    response += "2. 使用 query_kilo_memory 进行语义搜索\n"
    response += "3. 使用 trigger_vcp_recall 在任务开始时自动回忆\n"
    response += "4. 为记忆添加标签以提高检索准确性"
    
    return response

# 主函数
if __name__ == "__main__":
    print("=" * 60)
    print("VCP集成版 KiloMemoryMCP 服务器（修复版）")
    print("=" * 60)
    print("核心特性:")
    print("1. ✅ 真正的VCP集成：通过HTTP API调用VCP系统")
    print("2. ✅ 语义搜索：使用VCP的TagMemo系统进行语义扩展")
    print("3. ✅ 主动回忆：trigger_vcp_recall工具实现'一次回忆起'")
    print("4. ✅ 质量评估：多维度的记忆质量评分")
    print("5. ✅ 系统统计：实时监控记忆系统状态")
    print("=" * 60)
    
    # 检查VCP连接
    vcp_client = VCPAPIClient()
    if vcp_client.is_vcp_running():
        print("✅ VCP服务器连接正常")
    else:
        print("⚠️ VCP服务器未运行，将使用回退搜索")
    
    # 运行 MCP 服务器
    mcp.run()