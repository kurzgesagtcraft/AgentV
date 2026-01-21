"""
VCP增强版KiloMemoryMCP服务器（直接集成版）
直接调用VCPToolBox的KnowledgeBaseManager，避免HTTP API调用问题
"""

import os
import sys
import json
import sqlite3
import datetime
import hashlib
import re
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

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_VCP_Enhanced_Fixed")

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

# 直接集成VCPToolBox的KnowledgeBaseManager
class VCPDirectIntegration:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.knowledge_base = None
        self.embedding_utils = None
        self.text_chunker = None
        self._load_vcp_modules()
    
    def _load_vcp_modules(self):
        """直接加载VCPToolBox模块"""
        try:
            # 添加项目根目录到Python路径
            sys.path.insert(0, self.project_root)
            
            # 尝试加载KnowledgeBaseManager
            from KnowledgeBaseManager import KnowledgeBaseManager
            self.knowledge_base = KnowledgeBaseManager
            
            # 尝试加载EmbeddingUtils
            from EmbeddingUtils import getEmbeddingsBatch, getSingleEmbedding
            self.get_embeddings_batch = getEmbeddingsBatch
            self.get_single_embedding = getSingleEmbedding
            
            # 尝试加载TextChunker
            from TextChunker import chunkText
            self.chunk_text = chunkText
            
            print("✅ VCPToolBox模块加载成功")
            return True
            
        except Exception as e:
            print(f"❌ 加载VCPToolBox模块失败: {e}")
            print("💡 尝试备用加载方式...")
            
            # 备用加载方式：直接导入
            try:
                # 动态导入
                import importlib.util
                
                # 导入KnowledgeBaseManager
                kb_path = os.path.join(self.project_root, "KnowledgeBaseManager.js")
                if os.path.exists(kb_path):
                    print(f"找到KnowledgeBaseManager.js，但这是JavaScript模块，无法直接导入")
                
                return False
            except Exception as e2:
                print(f"❌ 备用加载也失败: {e2}")
                return False
    
    def is_vcp_available(self) -> bool:
        """检查VCP是否可用"""
        return self.knowledge_base is not None
    
    def search_knowledge(self, query: str, limit: int = 10, tag_boost: float = 0.5) -> List[Dict]:
        """直接调用KnowledgeBaseManager进行搜索"""
        if not self.is_vcp_available():
            print("❌ VCP知识库不可用")
            return []
        
        try:
            # 获取查询向量
            query_vector = self.get_single_embedding(query, {
                'apiKey': os.environ.get('API_Key', ''),
                'apiUrl': os.environ.get('API_URL', ''),
                'model': os.environ.get('WhitelistEmbeddingModel', 'text-embedding-3-small')
            })
            
            if not query_vector:
                print("❌ 查询向量化失败")
                return []
            
            # 执行搜索
            results = self.knowledge_base.search(query_vector, limit, tag_boost)
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.get("text", ""),
                    "sourceFile": result.get("sourceFile", ""),
                    "score": result.get("score", 0.0),
                    "diary_name": result.get("sourceFile", "").split("/")[-2] if "/" in result.get("sourceFile", "") else "VCP知识库",
                    "matchedTags": result.get("matchedTags", []),
                    "boostFactor": result.get("boostFactor", 0),
                    "tagMatchScore": result.get("tagMatchScore", 0),
                    "tagMatchCount": result.get("tagMatchCount", 0)
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ 搜索知识库失败: {e}")
            return []
    
    def store_to_knowledge_base(self, content: str, tags: List[str] = None) -> bool:
        """将记忆存储到VCP知识库"""
        if not self.is_vcp_available():
            print("❌ VCP知识库不可用")
            return False
        
        try:
            # 创建临时文件存储记忆
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            memory_id = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
            filename = f"KiloMemory_{timestamp}_{memory_id}.md"
            
            # 确定存储目录
            kb_root = os.path.join(self.project_root, "dailynote")
            memory_subdir = "KiloMemory"
            memory_dir = os.path.join(kb_root, memory_subdir)
            os.makedirs(memory_dir, exist_ok=True)
            
            filepath = os.path.join(memory_dir, filename)
            
            # 构建Markdown内容
            tag_str = ", ".join(tags) if tags else "KiloMemory"
            md_content = f"""# Kilo Memory - {datetime.datetime.now().isoformat()}

## 内容
{content}

## 元数据
- **记忆ID**: {memory_id}
- **存储时间**: {datetime.datetime.now().isoformat()}
- **标签**: {tag_str}
- **来源**: KiloMemoryMCP

Tag: {tag_str}
"""
            
            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            print(f"✅ 记忆已存储到VCP知识库: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ 存储到知识库失败: {e}")
            return False
    
    def trigger_active_recall(self, context: str, max_memories: int = 5) -> Dict:
        """触发主动回忆"""
        if not self.is_vcp_available():
            return {"success": False, "error": "VCP知识库不可用"}
        
        try:
            # 提取关键词
            keywords = self._extract_keywords(context)
            
            # 构建搜索查询
            search_query = self._build_recall_query(context, keywords)
            
            # 搜索知识库
            results = self.search_knowledge(search_query, max_memories * 2, 0.7)
            
            # 过滤和排序结果
            relevant_results = []
            for result in results:
                if result.get("score", 0) >= 0.3:  # 相关性阈值
                    relevant_results.append({
                        "text": result.get("text", ""),
                        "score": result.get("score", 0),
                        "source": result.get("sourceFile", ""),
                        "relevance": self._classify_relevance(result.get("score", 0)),
                        "matchedTags": result.get("matchedTags", []),
                        "timestamp": datetime.datetime.now().isoformat()
                    })
            
            # 限制数量
            relevant_results = relevant_results[:max_memories]
            
            # 构建回忆总结
            summary = self._build_recall_summary(context, relevant_results)
            
            return {
                "success": True,
                "context": context,
                "memories": relevant_results,
                "summary": summary,
                "stats": {
                    "totalFound": len(results),
                    "relevantFound": len(relevant_results),
                    "averageRelevance": sum(r["score"] for r in relevant_results) / len(relevant_results) if relevant_results else 0
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取逻辑
        words = text.lower() \
            .replace(/[^\w\u4e00-\u9fa5\s]/g, ' ') \
            .split(/\s+/) \
            .filter(word => word.length > 1)
        
        # 去重并返回前10个关键词
        return list(set(words))[:10]
    
    def _build_recall_query(self, context: str, keywords: List[str]) -> str:
        """构建回忆查询"""
        if keywords:
            return f"{context} {' '.join(keywords)}"
        return context
    
    def _classify_relevance(self, score: float) -> str:
        """分类相关性"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def _build_recall_summary(self, context: str, memories: List[Dict]) -> str:
        """构建回忆总结"""
        if not memories:
            return f"基于当前上下文\"{context[:50]}...\"，没有找到相关的历史记忆。"
        
        memory_count = len(memories)
        avg_relevance = sum(m["score"] for m in memories) / memory_count
        relevance_level = self._classify_relevance(avg_relevance)
        
        tag_set = set()
        for memory in memories:
            for tag in memory.get("matchedTags", []):
                tag_set.add(tag)
        
        top_tags = list(tag_set)[:5]
        
        summary = f"基于当前上下文，系统主动回忆了 {memory_count} 个相关记忆（平均相关性：{relevance_level}）。"
        if top_tags:
            summary += f" 相关标签：{'、'.join(top_tags)}"
        
        return summary

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

# 主记忆管理器（直接集成VCP）
class VCPEnhancedMemoryManager:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.db_path = DB_PATH
        self.vcp_integration = VCPDirectIntegration()
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
            
            # 同时存储到VCP知识库
            vcp_success = self.vcp_integration.store_to_knowledge_base(content, tags)
            
            return {
                "success": True,
                "memory_id": memory_id,
                "filepath": filepath,
                "vcp_stored": vcp_success,
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
            
            # 策略1：使用VCP直接集成搜索（如果可用）
            if query and self.vcp_integration.is_vcp_available():
                vcp_results = self.vcp_integration.search_knowledge(query, limit * 2, 0.5)
                
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
                            "search_method": "vcp_direct"
                        })
            
            # 策略2：文件系统搜索（回退）
            if len(results) < limit:
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
                    "vcp_direct": 3.0,
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
            
            vcp_available = self.vcp_integration.is_vcp_available()
            
            return {
                "total_memories": len(memory_files),
                "recent_7_days": recent_count,
                "vcp_available": vcp_available,
                "memory_dir": self.memory_dir
            }
            
        except Exception as e:
            return {"error": f"获取统计失败: {str(e)}"}

# 工具函数
def ensure_memory_dir():
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)

# 初始化记忆管理器
memory_manager = VCPEnhancedMemoryManager()

# MCP工具定义
@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 dailynote 文件夹（VCP增强版）。
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
        
        response = f"""✅ 记忆存储成功（VCP增强版）！

记忆ID: {memory_id}
存储位置: {result['filepath']}
VCP知识库: {'✅ 已同步' if result.get('vcp_stored', False) else '⚠️ 同步失败'}
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
    查询 Kilo Code 的记忆（VCP增强版）。
    使用VCP直接集成进行语义搜索，支持质量过滤和记忆类型识别。
    
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
        response = f"🔍 使用VCP增强搜索找到 {len(results)} 条与 '{query}' 相关的记忆:\n\n"
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
        method_icon = "🔗" if search_method == "vcp_direct" else "📁"
        
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

@mcp.tool()
def list_all_kilo_memories(limit: int = 20) -> str:
    """
    列出最近的 Kilo Code 记忆（VCP增强版）。
    :param limit: 返回数量限制
    """
    return query_kilo_memory("", limit)

@mcp.tool()
def get_memory_stats() -> str:
    """
    获取VCP增强记忆系统的统计信息。
    """
    stats = memory_manager.get_memory_stats()
    
    if "error" in stats:
        return f"获取统计信息失败: {stats['error']}"
    
    response = "📊 VCP增强记忆系统统计报告\n\n"
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

@mcp.tool()
def trigger_vcp_recall(context: str, max_memories: int = 5) -> str:
    """
    触发VCP主动回忆功能，在任务开始时自动回忆相关记忆。
    
    💡 使用场景：
    1. 在开始新任务时调用此工具，自动回忆相关经验
    2. 在遇到问题时调用，寻找类似问题的解决方案
    3. 在决策时调用，获取历史决策依据
    
    :param context: 当前任务或对话上下文
    :param max_memories: 最大回忆数量（默认5）
    """
    try:
        result = memory_manager.vcp_integration.trigger_active_recall(context, max_memories)
        
        if not result.get("success", False):
            return f"❌ 主动回忆失败: {result.get('error', '未知错误')}"
        
        memories = result.get("memories", [])
        summary = result.get("summary", "")
        stats = result.get("stats", {})
        
        if not memories:
            return f"🔍 基于当前上下文，没有找到相关的历史记忆。\n\n上下文: {context[:100]}..."
        
        response = f"🧠 VCP主动回忆结果（基于上下文）\n\n"
        response += f"📋 上下文: {context[:150]}...\n\n"
        response += f"📊 统计: 找到 {stats.get('relevantFound', 0)} 个相关记忆（共搜索 {stats.get('totalFound', 0)} 个）\n\n"
        response += f"📝 回忆总结: {summary}\n\n"
        response += "🔍 相关记忆:\n\n"
        
        for i, memory in enumerate(memories, 1):
            score = memory.get("score", 0)
            relevance = memory.get("relevance", "unknown")
            source = memory.get("source", "VCP知识库")
            text = memory.get("text", "")[:200] + "..." if len(memory.get("text", "")) > 200 else memory.get("text", "")
            
            relevance_icons = {
                "high": "🔥",
                "medium": "⭐",
                "low": "📝",
                "very_low": "📄"
            }
            relevance_icon = relevance_icons.get(relevance, "📄")
            
            response += f"{i}. {relevance_icon} 相关性: {relevance} (分数: {score:.3f})\n"
            response += f"   来源: {source}\n"
            response += f"   内容: {text}\n"
            
            matched_tags = memory.get("matchedTags", [])
            if matched_tags:
                response += f"   匹配标签: {', '.join(matched_tags[:3])}\n"
            
            response += "\n"
        
        response += "💡 使用建议:\n"
        response += "1. 这些记忆可以帮助您更好地理解当前任务\n"
        response += "2. 参考历史经验可以避免重复错误\n"
        response += "3. 使用 store_kilo_memory 存储新的重要发现\n"
        
        return response
        
    except Exception as e:
        return f"❌ 触发主动回忆时发生错误: {str(e)}"

# 主函数
if __name__ == "__main__":
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("VCP增强版 KiloMemoryMCP 服务器（直接集成版）\n")
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("核心特性:\n")
    sys.stderr.write("1. ✅ 直接VCP集成：直接调用KnowledgeBaseManager模块\n")
    sys.stderr.write("2. ✅ 语义搜索：使用VCP的TagMemo系统进行语义扩展\n")
    sys.stderr.write("3. ✅ 主动回忆：trigger_vcp_recall工具实现'一次回忆起'\n")
    sys.stderr.write("4. ✅ 质量评估：多维度的记忆质量评分\n")
    sys.stderr.write("5. ✅ 系统统计：实时监控记忆系统状态\n")
    sys.stderr.write("6. ✅ 双存储：同时存储到本地文件和VCP知识库\n")
    sys.stderr.write("=" * 60 + "\n")
    
    # 检查VCP集成状态
    sys.stderr.write("🔍 检查VCP集成状态...\n")
    sys.stderr.flush()
    
    if memory_manager.vcp_integration.is_vcp_available():
        sys.stderr.write("✅ VCP知识库集成正常\n")
        sys.stderr.flush()
    else:
        sys.stderr.write("⚠️ VCP知识库集成失败，将使用文件系统搜索\n")
        sys.stderr.write("💡 提示：确保VCPToolBox服务器正在运行\n")
        sys.stderr.flush()
    
    # 运行 MCP 服务器
    sys.stderr.write("\n🚀 启动KiloMemoryMCP增强版服务器...\n")
    sys.stderr.flush()
    mcp.run()
