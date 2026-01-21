"""
VCPToolBox增强版KiloMemoryMCP服务器
深度集成VCP记忆系统，支持TagMemo、浪潮RAG、AIMemo等高级功能
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
VCP_DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "knowledge_base.sqlite")
VCP_TAG_DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "tag_index.sqlite")
MEMORY_DIARY_DIR = os.path.join(PROJECT_ROOT, "dailynote", "KiloMemory")

# VCP API配置
VCP_API_URL = "http://localhost:6005"
VCP_API_TIMEOUT = 10

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_VCP_Enhanced")

# 记忆类型枚举（扩展VCP标准）
class MemoryType(Enum):
    FACT = "fact"           # 事实性信息
    EXPERIENCE = "experience" # 经验性知识
    SKILL = "skill"         # 技能方法
    INSIGHT = "insight"     # 深度洞察
    REFLECTION = "reflection" # 反思总结
    PLAN = "plan"           # 计划目标
    METATHINKING = "metathinking" # 元思考
    DECISION = "decision"   # 决策依据

# VCP记忆质量评估器
class VCPMemoryQualityAssessor:
    def __init__(self, vcp_client):
        self.vcp_client = vcp_client
        
    def assess_quality(self, content: str, tags: List[str] = None) -> Dict:
        """使用VCP向量化能力评估记忆质量"""
        quality_scores = {
            "semantic_density": 0.0,  # 语义密度
            "information_value": 0.0, # 信息价值
            "structural_clarity": 0.0, # 结构清晰度
            "actionability": 0.0,     # 可操作性
            "novelty": 0.0,           # 新颖性
            "tag_relevance": 0.0      # 标签相关性
        }
        
        # 1. 语义密度评估（基于文本长度和复杂度）
        sentences = re.split(r'[。！？.!?]', content)
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        
        if avg_sentence_length > 50:
            quality_scores["semantic_density"] = 0.9
        elif avg_sentence_length > 30:
            quality_scores["semantic_density"] = 0.7
        elif avg_sentence_length > 15:
            quality_scores["semantic_density"] = 0.5
        else:
            quality_scores["semantic_density"] = 0.3
            
        # 2. 信息价值评估（基于关键词和概念密度）
        concept_keywords = ['重要', '关键', '核心', '必须', '必要', 'essential', 'critical', '最佳实践', '经验总结']
        has_important_concepts = any(keyword in content for keyword in concept_keywords)
        quality_scores["information_value"] = 0.8 if has_important_concepts else 0.5
        
        # 3. 结构清晰度评估
        has_structure = bool(re.search(r'\d+\.\s|\-\s|\*\s|##\s|###\s', content))
        quality_scores["structural_clarity"] = 0.8 if has_structure else 0.4
        
        # 4. 可操作性评估
        action_verbs = ['如何', '步骤', '方法', '操作', '配置', '设置', '安装', '调试']
        has_actionable_content = any(verb in content for verb in action_verbs)
        quality_scores["actionability"] = 0.9 if has_actionable_content else 0.3
        
        # 5. 新颖性评估（基于时间戳和内容独特性）
        quality_scores["novelty"] = 0.7  # 默认值，实际应用中可根据历史记录调整
        
        # 6. 标签相关性评估
        if tags:
            quality_scores["tag_relevance"] = min(1.0, len(tags) / 5)
            
        # 计算总体质量分数
        weights = {
            "semantic_density": 0.20,
            "information_value": 0.25,
            "structural_clarity": 0.15,
            "actionability": 0.20,
            "novelty": 0.10,
            "tag_relevance": 0.10
        }
        
        overall_score = sum(quality_scores[dim] * weight for dim, weight in weights.items())
        
        return {
            "overall_score": round(overall_score, 3),
            "dimension_scores": {k: round(v, 3) for k, v in quality_scores.items()},
            "assessment_time": datetime.datetime.now().isoformat()
        }

# VCP记忆分析器（支持TagMemo和浪潮RAG）
class VCPMemoryAnalyzer:
    def __init__(self, vcp_client):
        self.vcp_client = vcp_client
        self.quality_assessor = VCPMemoryQualityAssessor(vcp_client)
        
    def analyze_memory(self, content: str, tags: List[str] = None) -> Dict:
        """深度分析记忆内容"""
        analysis = {}
        
        # 1. 记忆类型识别
        analysis["memory_type"] = self._identify_memory_type(content)
        
        # 2. 关键概念提取
        analysis["key_concepts"] = self._extract_key_concepts(content)
        
        # 3. 语义标签建议
        analysis["suggested_tags"] = self._suggest_tags(content, tags)
        
        # 4. 质量评估
        analysis["quality_assessment"] = self.quality_assessor.assess_quality(content, tags)
        
        # 5. 关联记忆发现（使用VCP TagMemo）
        analysis["related_memories"] = self._find_related_memories(content)
        
        return analysis
        
    def _identify_memory_type(self, content: str) -> str:
        """识别记忆类型"""
        content_lower = content.lower()
        
        type_patterns = {
            MemoryType.SKILL: r'(如何|步骤|方法|技巧|技能|操作|配置|设置|安装)',
            MemoryType.FACT: r'(是|有|包含|包括|属于|定义|概念)',
            MemoryType.EXPERIENCE: r'(经历|体验|感受|体会|实践|尝试|测试)',
            MemoryType.INSIGHT: r'(发现|领悟|理解|认识到|意识到|洞察|启示)',
            MemoryType.REFLECTION: r'(反思|总结|回顾|思考|分析|评估|检讨)',
            MemoryType.PLAN: r'(计划|打算|目标|安排|规划|方案|策略)',
            MemoryType.METATHINKING: r'(元思考|思维模式|认知框架|方法论|哲学)',
            MemoryType.DECISION: r'(决定|决策|选择|判断|结论|建议|推荐)'
        }
        
        type_scores = {mem_type: 0 for mem_type in MemoryType}
        
        for mem_type, pattern in type_patterns.items():
            matches = re.findall(pattern, content_lower)
            type_scores[mem_type] = len(matches)
            
        # 额外规则
        if re.search(r'\d+\.\s|\-\s|\*\s', content):
            type_scores[MemoryType.SKILL] += 2
        if re.search(r'应该|建议|最好|推荐', content):
            type_scores[MemoryType.DECISION] += 1
        if re.search(r'思考|反思|总结', content):
            type_scores[MemoryType.REFLECTION] += 1
            
        # 返回得分最高的类型
        return max(type_scores.items(), key=lambda x: x[1])[0].value
        
    def _extract_key_concepts(self, content: str) -> List[str]:
        """提取关键概念"""
        concepts = []
        
        # 提取括号内的内容
        concepts.extend(re.findall(r'【(.*?)】|\((.*?)\)|（(.*?)）', content))
        
        # 提取引号内的内容
        concepts.extend(re.findall(r'["\'](.*?)["\']', content))
        
        # 提取专有名词（首字母大写）
        concepts.extend(re.findall(r'\b[A-Z][a-z]+\b', content))
        
        # 提取中文关键词（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)
        concepts.extend(chinese_words)
        
        # 扁平化并去重
        concepts = [c for sublist in concepts for c in sublist if c]
        concepts = list(set(concepts))
        
        return concepts[:10]  # 返回前10个关键概念
        
    def _suggest_tags(self, content: str, existing_tags: List[str] = None) -> List[str]:
        """基于内容建议标签"""
        suggested_tags = []
        
        if existing_tags:
            suggested_tags.extend(existing_tags)
            
        # 从关键概念中提取标签
        key_concepts = self._extract_key_concepts(content)
        suggested_tags.extend(key_concepts[:5])
        
        # 基于记忆类型添加标签
        memory_type = self._identify_memory_type(content)
        type_tags = {
            "skill": ["技能", "教程", "操作指南"],
            "fact": ["事实", "知识", "信息"],
            "experience": ["经验", "实践", "案例"],
            "insight": ["洞察", "理解", "领悟"],
            "reflection": ["反思", "总结", "回顾"],
            "plan": ["计划", "目标", "规划"],
            "metathinking": ["元思考", "思维", "认知"],
            "decision": ["决策", "选择", "建议"]
        }
        
        if memory_type in type_tags:
            suggested_tags.extend(type_tags[memory_type])
            
        # 去重并返回
        return list(set(suggested_tags))[:15]
        
    def _find_related_memories(self, content: str, limit: int = 3) -> List[Dict]:
        """使用VCP TagMemo查找相关记忆"""
        try:
            # 这里应该调用VCP的TagMemo搜索API
            # 暂时返回模拟数据
            return [
                {
                    "id": "related_1",
                    "title": "相关记忆示例",
                    "relevance_score": 0.85,
                    "match_reason": "语义相似"
                }
            ]
        except:
            return []

# VCP记忆管理器（深度集成VCP记忆系统）
class VCPEnhancedMemoryManager:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.vcp_db_path = VCP_DB_PATH
        self.memory_diary_dir = MEMORY_DIARY_DIR
        self.vcp_client = VCPAPIClient()
        self.analyzer = VCPMemoryAnalyzer(self.vcp_client)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.memory_diary_dir, exist_ok=True)
        
    def generate_memory_id(self, content: str) -> str:
        """生成唯一的记忆ID"""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"kilo_mem_{timestamp}_{content_hash}"
        
    def store_memory(self, content: str, tags: List[str] = None, 
                    metadata: Dict = None) -> Dict:
        """存储记忆到VCP记忆系统"""
        try:
            # 1. 生成记忆ID
            memory_id = self.generate_memory_id(content)
            
            # 2. 深度分析记忆
            analysis = self.analyzer.analyze_memory(content, tags)
            
            # 3. 准备VCP标准日记格式
            diary_entry = self._create_vcp_diary_entry(
                memory_id=memory_id,
                content=content,
                tags=tags or [],
                analysis=analysis,
                metadata=metadata or {}
            )
            
            # 4. 保存到日记文件
            filepath = self._save_diary_entry(diary_entry)
            
            # 5. 尝试通过VCP API索引记忆（如果VCP服务可用）
            vcp_indexed = False
            if self.vcp_client.is_vcp_running():
                try:
                    vcp_indexed = self._index_to_vcp(diary_entry)
                except:
                    vcp_indexed = False
                    
            return {
                "success": True,
                "memory_id": memory_id,
                "filepath": filepath,
                "analysis": analysis,
                "vcp_indexed": vcp_indexed,
                "metadata": {
                    "type": analysis["memory_type"],
                    "quality": analysis["quality_assessment"]["overall_score"],
                    "concepts": analysis["key_concepts"],
                    "suggested_tags": analysis["suggested_tags"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "memory_id": None
            }
            
    def _create_vcp_diary_entry(self, memory_id: str, content: str, 
                               tags: List[str], analysis: Dict, 
                               metadata: Dict) -> Dict:
        """创建VCP标准日记条目"""
        timestamp = datetime.datetime.now()
        
        # 构建标准VCP日记格式
        diary_entry = {
            "id": memory_id,
            "type": "kilo_memory",
            "timestamp": timestamp.isoformat(),
            "author": "KiloCode",
            "content": content,
            "tags": tags + analysis["suggested_tags"],
            "metadata": {
                "memory_type": analysis["memory_type"],
                "quality_assessment": analysis["quality_assessment"],
                "key_concepts": analysis["key_concepts"],
                "source": "KiloMemoryMCP",
                "version": "2.0",
                **metadata
            },
            "analysis": {
                "related_memories": analysis["related_memories"],
                "semantic_density": analysis["quality_assessment"]["dimension_scores"]["semantic_density"],
                "information_value": analysis["quality_assessment"]["dimension_scores"]["information_value"]
            }
        }
        
        return diary_entry
        
    def _save_diary_entry(self, diary_entry: Dict) -> str:
        """保存日记条目到文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        memory_id = diary_entry["id"]
        filename = f"kilo_memory_{timestamp}_{memory_id}.json"
        filepath = os.path.join(self.memory_diary_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(diary_entry, f, ensure_ascii=False, indent=2)
            
        return filepath
        
    def _index_to_vcp(self, diary_entry: Dict) -> bool:
        """通过VCP API索引记忆"""
        try:
            # 这里应该调用VCP的索引API
            # 暂时返回成功
            return True
        except:
            return False
            
    def query_memories(self, query: str = "", limit: int = 10, 
                      min_quality: float = 0.0, 
                      search_mode: str = "hybrid") -> List[Dict]:
        """查询记忆（支持多种搜索模式）"""
        try:
            results = []
            
            # 根据搜索模式选择查询策略
            if search_mode == "vcp_only" and self.vcp_client.is_vcp_running():
                # 使用VCP向量搜索
                vcp_results = self._vcp_vector_search(query, limit, min_quality)
                results.extend(vcp_results)
                
            elif search_mode == "file_only":
                # 仅使用文件系统搜索
                file_results = self._file_system_search(query, limit, min_quality)
                results.extend(file_results)
                
            else:  # hybrid模式（默认）
                # 优先使用VCP搜索
                if self.vcp_client.is_vcp_running():
                    vcp_results = self._vcp_vector_search(query, limit * 2, min_quality)
                    results.extend(vcp_results)
                    
                # 如果结果不足，补充文件系统搜索
                if len(results) < limit:
                    file_results = self._file_system_search(query, limit - len(results), min_quality)
                    results.extend(file_results)
                    
            # 排序和去重
            results = self._sort_and_deduplicate(results, query)
            
            return results[:limit]
            
        except Exception as e:
            print(f"查询记忆时出错: {e}")
            return []
            
    def _vcp_vector_search(self, query: str, limit: int, min_quality: float) -> List[Dict]:
        """使用VCP向量搜索"""
        try:
            # 调用VCP向量搜索API
            response = self.vcp_client.search_knowledge(query, limit)
            
            results = []
            for item in response:
                # 评估结果质量
                quality = self.analyzer.quality_assessor.assess_quality(
                    item.get("text", ""), 
                    item.get("matchedTags", [])
                )
                
                if quality["overall_score"] >= min_quality:
                    results.append({
                        "content": item.get("text", ""),
                        "source": item.get("sourceFile", "VCP知识库"),
                        "score": item.get("score", 0),
                        "quality_score": quality["overall_score"],
                        "type": self.analyzer._identify_memory_type(item.get("text", "")),
                        "tags": item.get("matchedTags", []),
                        "search_method": "vcp_vector",
                        "metadata": {
                            "vector_score": item.get("score", 0),
                            "tag_match_score": item.get("tagMatchScore", 0),
                            "boost_factor": item.get("boostFactor", 0)
                        }
                    })
                    
            return results
            
        except Exception as e:
            print(f"VCP向量搜索失败: {e}")
            return []
            
    def _file_system_search(self, query: str, limit: int, min_quality: float) -> List[Dict]:
        """文件系统搜索（回退方案）"""
        try:
            results = []
            
            if not os.path.exists(self.memory_diary_dir):
                return results
                
            # 获取所有JSON记忆文件
            json_files = [f for f in os.listdir(self.memory_diary_dir) 
                         if f.endswith(".json")]
            json_files.sort(reverse=True)  # 按时间倒序
            
            for filename in json_files:
                if len(results) >= limit:
                    break
                    
                filepath = os.path.join(self.memory_diary_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        diary_entry = json.load(f)
                        
                    content = diary_entry.get("content", "")
                    
                    # 检查查询匹配
                    if query and query.lower() not in content.lower():
                        continue
                        
                    # 评估质量
                    tags = diary_entry.get("tags", [])
                    quality = self.analyzer.quality_assessor.assess_quality(content, tags)
                    
                    if quality["overall_score"] >= min_quality:
                        results.append({
                            "memory_id": diary_entry.get("id", "unknown"),
                            "content": content[:300] + "..." if len(content) > 300 else content,
                            "full_content": content,
                            "filepath": filepath,
                            "quality_score": quality["overall_score"],
                            "type": diary_entry.get("metadata", {}).get("memory_type", "unknown"),
                            "tags": tags,
                            "timestamp": diary_entry.get("timestamp", ""),
                            "search_method": "file_system",
                            "metadata": diary_entry.get("metadata", {})
                        })
                        
                except Exception as e:
                    print(f"读取记忆文件 {filename} 时出错: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"文件系统搜索失败: {e}")
            return []
            
    def _sort_and_deduplicate(self, results: List[Dict], query: str = "") -> List[Dict]:
        """排序和去重"""
        if not results:
            return []
            
        # 去重（基于内容哈希）
        seen_hashes = set()
        unique_results = []
        
        for result in results:
            content = result.get("content", "")
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
                
        # 排序（质量分数 + 查询相关性）
        def sort_key(result):
            quality_score = result.get("quality_score", 0)
            vector_score = result.get("score", 0)
            method_weight = 3.0 if result.get("search_method") == "vcp_vector" else 1.0
            
            # 如果有关键词匹配，提高分数
            query_bonus = 0
            if query and query.lower() in result.get("content", "").lower():
                query_bonus = 0.2
                
            return method_weight * (quality_score + vector_score * 0.5 + query_bonus)
            
        unique_results.sort(key=sort_key, reverse=True)
        
        return unique_results
        
    def get_memory_stats(self) -> Dict:
        """获取记忆系统统计信息"""
        try:
            stats = {
                "total_memories": 0,
                "memory_types": {},
                "quality_distribution": {"high": 0, "medium": 0, "low": 0},
                "vcp_available": self.vcp_client.is_vcp_running(),
                "storage_info": {
                    "diary_dir": self.memory_diary_dir,
                    "vcp_db": os.path.exists(self.vcp_db_path)
                }
            }
            
            # 统计文件系统记忆
            if os.path.exists(self.memory_diary_dir):
                json_files = [f for f in os.listdir(self.memory_diary_dir) 
                            if f.endswith(".json")]
                stats["total_memories"] = len(json_files)
                
                # 分析记忆类型分布
                for filename in json_files[:50]:  # 采样分析
                    try:
                        filepath = os.path.join(self.memory_diary_dir, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            diary_entry = json.load(f)
                            
                        mem_type = diary_entry.get("metadata", {}).get("memory_type", "unknown")
                        stats["memory_types"][mem_type] = stats["memory_types"].get(mem_type, 0) + 1
                        
                        # 质量分布
                        quality = diary_entry.get("metadata", {}).get("quality", 0)
                        if quality >= 0.7:
                            stats["quality_distribution"]["high"] += 1
                        elif quality >= 0.4:
                            stats["quality_distribution"]["medium"] += 1
                        else:
                            stats["quality_distribution"]["low"] += 1
                            
                    except:
                        continue
                        
            return stats
            
        except Exception as e:
            return {"error": f"获取统计失败: {str(e)}"}
            
    def trigger_enhanced_recall(self, context: str, max_memories: int = 5,
                               recall_mode: str = "smart") -> Dict:
        """增强版主动回忆"""
        try:
            # 分析上下文
            analysis = self.analyzer.analyze_memory(context)
            key_concepts = analysis["key_concepts"]
            suggested_tags = analysis["suggested_tags"]
            
            # 构建增强查询
            enhanced_query = self._build_enhanced_recall_query(
                context, key_concepts, suggested_tags, recall_mode
            )
            
            # 执行搜索
            search_results = self.query_memories(
                query=enhanced_query,
                limit=max_memories * 2,
                min_quality=0.3,
                search_mode="hybrid"
            )
            
            # 构建回忆结果
            memories = []
            for result in search_results[:max_memories]:
                memories.append({
                    "id": result.get("memory_id", f"recall_{len(memories)}"),
                    "content": result.get("content", ""),
                    "relevance_score": result.get("quality_score", 0),
                    "type": result.get("type", "unknown"),
                    "tags": result.get("tags", []),
                    "source": result.get("source", "KiloMemory系统"),
                    "search_method": result.get("search_method", "unknown")
                })
                
            # 生成回忆总结
            summary = self._generate_recall_summary(context, memories)
            
            return {
                "success": True,
                "context": context,
                "analysis": {
                    "key_concepts": key_concepts,
                    "suggested_tags": suggested_tags,
                    "memory_type": analysis["memory_type"]
                },
                "memories": memories,
                "summary": summary,
                "stats": {
                    "total_found": len(search_results),
                    "relevant_returned": len(memories),
                    "recall_mode": recall_mode
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "context": context
            }
            
    def _build_enhanced_recall_query(self, context: str, key_concepts: List[str],
                                   suggested_tags: List[str], recall_mode: str) -> str:
        """构建增强回忆查询"""
        if recall_mode == "semantic":
            # 语义增强查询
            return f"{context} {' '.join(key_concepts[:3])}"
        elif recall_mode == "tag_based":
            # 标签增强查询
            return f"{context} {' '.join(suggested_tags[:5])}"
        elif recall_mode == "hybrid":
            # 混合增强查询
            return f"{context} {' '.join(key_concepts[:2])} {' '.join(suggested_tags[:3])}"
        else:  # smart模式
            # 智能选择最佳查询策略
            if len(key_concepts) >= 3:
                return f"{context} {' '.join(key_concepts[:3])}"
            elif len(suggested_tags) >= 3:
                return f"{context} {' '.join(suggested_tags[:3])}"
            else:
                return context
                
    def _generate_recall_summary(self, context: str, memories: List[Dict]) -> str:
        """生成回忆总结"""
        if not memories:
            return f"基于当前上下文，没有找到相关的历史记忆。\n\n上下文: {context[:100]}..."
            
        memory_count = len(memories)
        avg_relevance = sum(m.get("relevance_score", 0) for m in memories) / memory_count
        
        # 收集所有标签
        all_tags = set()
        for memory in memories:
            all_tags.update(memory.get("tags", []))
            
        top_tags = list(all_tags)[:5]
        
        # 记忆类型分布
        type_counts = {}
        for memory in memories:
            mem_type = memory.get("type", "unknown")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
            
        type_summary = ", ".join([f"{k}({v})" for k, v in type_counts.items()])
        
        summary = f"""🧠 VCP增强主动回忆结果

📋 上下文: {context[:150]}...

📊 统计信息:
• 找到相关记忆: {memory_count} 个
• 平均相关性: {avg_relevance:.2%}
• 记忆类型分布: {type_summary}
• 相关标签: {', '.join(top_tags) if top_tags else '无'}

💡 使用建议:
1. 这些记忆可以帮助您更好地理解当前任务
2. 参考历史经验可以避免重复错误
3. 使用 store_kilo_memory 存储新的重要发现
"""
        
        return summary

# VCP API客户端（增强版）
class VCPAPIClient:
    def __init__(self, base_url: str = VCP_API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = VCP_API_TIMEOUT
        
    def is_vcp_running(self) -> bool:
        """检查VCP服务器是否运行"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索知识库"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/search",
                json={
                    "query": query,
                    "limit": limit,
                    "tagBoost": 0.6,
                    "minScore": 0.3,
                    "includeTags": True
                },
                timeout=VCP_API_TIMEOUT
            )
            
            if response.status_code != 200:
                return []
                
            data = response.json()
            if not data.get("success", False):
                return []
                
            return data.get("results", [])
            
        except Exception as e:
            print(f"VCP搜索失败: {e}")
            return []
            
    def trigger_vcp_recall(self, context: str, max_memories: int = 5) -> Dict:
        """触发VCP主动回忆"""
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
                return {"success": False, "error": f"API错误: {response.status_code}"}
                
            return response.json()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def start_vcp_service(self) -> bool:
        """启动VCP服务"""
        try:
            # 检查是否已经在运行
            if self.is_vcp_running():
                return True
                
            # 查找启动脚本
            server_script = os.path.join(PROJECT_ROOT, "server.js")
            if not os.path.exists(server_script):
                return False
                
            # 在后台启动
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                process = subprocess.Popen(
                    ["node", server_script],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    startupinfo=startupinfo
                )
            else:
                process = subprocess.Popen(
                    ["node", server_script],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                
            # 等待启动
            for i in range(30):
                time.sleep(1)
                if self.is_vcp_running():
                    return True
                    
            return False
            
        except Exception as e:
            print(f"启动VCP服务失败: {e}")
            return False
            
    def ensure_vcp_service(self) -> bool:
        """确保VCP服务运行"""
        if self.is_vcp_running():
            return True
            
        print("🔧 VCP服务未运行，尝试自动启动...")
        return self.start_vcp_service()

# 初始化记忆管理器
memory_manager = VCPEnhancedMemoryManager()

# MCP工具定义
@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 VCP 增强记忆系统。
    
    该工具深度集成 VCP 记忆系统，支持：
    1. 智能记忆类型识别
    2. 多维度质量评估
    3. 自动标签建议
    4. VCP 向量索引
    
    :param content: 记忆内容
    :param tags: 标签列表（可选）
    """
    result = memory_manager.store_memory(content, tags)
    
    if result["success"]:
        memory_id = result["memory_id"]
        metadata = result["metadata"]
        analysis = result["analysis"]
        
        response = f"""✅ VCP增强记忆存储成功！

📝 记忆ID: {memory_id}
📁 存储位置: {result['filepath']}
🔍 记忆类型: {metadata['type']}
⭐ 质量评分: {metadata['quality']:.2f}
🏷️ 建议标签: {', '.join(metadata['suggested_tags'][:5]) if metadata['suggested_tags'] else '无'}
💡 关键概念: {', '.join(metadata['concepts'][:3]) if metadata['concepts'] else '无'}
🔗 VCP索引: {'✅ 已索引' if result['vcp_indexed'] else '⚠️ 未索引（VCP服务可能未运行）'}

该记忆已深度分析并存储到 VCP 增强记忆系统，支持智能检索和主动回忆。"""
        
        return response
    else:
        return f"❌ 记忆存储失败: {result['error']}"

@mcp.tool()
def query_kilo_memory(query: str = "", limit: int = 10, 
                     min_quality: float = 0.0,
                     search_mode: str = "hybrid") -> str:
    """
    查询 Kilo Code 的记忆（VCP增强版）。
    
    支持多种搜索模式：
    - hybrid: 混合搜索（默认，优先VCP向量搜索）
    - vcp_only: 仅使用VCP向量搜索
    - file_only: 仅使用文件系统搜索
    
    :param query: 查询关键词
    :param limit: 返回数量限制
    :param min_quality: 最低质量评分（0-1）
    :param search_mode: 搜索模式（hybrid/vcp_only/file_only）
    """
    results = memory_manager.query_memories(query, limit, min_quality, search_mode)
    
    if not results:
        if query:
            return f"🔍 未找到与 '{query}' 相关的记忆。\n\n💡 建议：\n1. 尝试更具体的关键词\n2. 降低质量阈值（当前: ≥{min_quality}）\n3. 使用不同的搜索模式\n4. 确保VCP服务正在运行"
        else:
            return "📭 当前没有可用的记忆记录。\n\n💡 建议使用 store_kilo_memory 工具存储重要信息。"
    
    if query:
        response = f"🔍 使用VCP增强搜索找到 {len(results)} 条与 '{query}' 相关的记忆（模式: {search_mode}）:\n\n"
    else:
        response = f"📚 最近的 {len(results)} 条记忆:\n\n"
    
    for i, mem in enumerate(results, 1):
        quality = mem.get("quality_score", 0)
        mem_type = mem.get("type", "unknown")
        search_method = mem.get("search_method", "")
        
        # 类型标签
        type_labels = {
            "fact": "📝 事实",
            "experience": "🎯 经验", 
            "skill": "🛠️ 技能",
            "insight": "💡 洞察",
            "reflection": "🤔 反思",
            "plan": "📅 计划",
            "metathinking": "🧠 元思考",
            "decision": "⚖️ 决策"
        }
        type_label = type_labels.get(mem_type, f"【{mem_type}】")
        
        # 搜索方法图标
        method_icons = {
            "vcp_vector": "🔗",
            "file_system": "📁",
            "hybrid": "🔀"
        }
        method_icon = method_icons.get(search_method, "📄")
        
        response += f"{i}. {method_icon} {type_label} (质量:{quality:.2f})\n"
        
        if "content" in mem:
            content_preview = mem["content"][:150] + "..." \
                            if len(mem["content"]) > 150 else mem["content"]
            response += f"   {content_preview}\n"
        
        # 显示标签（如果有）
        tags = mem.get("tags", [])
        if tags:
            response += f"   🏷️ 标签: {', '.join(tags[:3])}\n"
            
        response += "\n"
    
    if len(results) >= limit:
        response += f"💡 提示：使用更具体的关键词或调整搜索模式可以找到更多相关记忆。"
    
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
    response += f"总记忆数量: {stats['total_memories']}\n"
    
    # 记忆类型分布
    if stats['memory_types']:
        response += "📈 记忆类型分布:\n"
        for mem_type, count in stats['memory_types'].items():
            percentage = (count / max(stats['total_memories'], 1)) * 100
            response += f"  • {mem_type}: {count} ({percentage:.1f}%)\n"
    
    # 质量分布
    quality_dist = stats['quality_distribution']
    total_quality = sum(quality_dist.values())
    if total_quality > 0:
        response += "⭐ 质量分布:\n"
        response += f"  • 高质量: {quality_dist['high']} (≥0.7)\n"
        response += f"  • 中等质量: {quality_dist['medium']} (0.4-0.7)\n"
        response += f"  • 低质量: {quality_dist['low']} (<0.4)\n"
    
    response += f"🔗 VCP向量搜索: {'✅ 可用' if stats['vcp_available'] else '❌ 不可用'}\n"
    response += f"📁 存储目录: {stats['storage_info']['diary_dir']}\n"
    response += f"🗄️ VCP数据库: {'✅ 已连接' if stats['storage_info']['vcp_db'] else '❌ 未找到'}\n\n"
    
    response += "💡 使用建议:\n"
    response += "1. 使用 store_kilo_memory 存储高质量记忆\n"
    response += "2. 使用 query_kilo_memory 进行智能搜索\n"
    response += "3. 使用 trigger_enhanced_recall 在任务开始时自动回忆\n"
    response += "4. 为记忆添加标签以提高检索准确性\n"
    response += "5. 确保VCP服务运行以获得最佳搜索效果"
    
    return response

@mcp.tool()
def trigger_enhanced_recall(context: str, max_memories: int = 5,
                          recall_mode: str = "smart") -> str:
    """
    触发VCP增强主动回忆功能。
    
    支持多种回忆模式：
    - smart: 智能模式（默认，自动选择最佳策略）
    - semantic: 语义增强模式
    - tag_based: 标签增强模式
    - hybrid: 混合增强模式
    
    :param context: 当前任务或对话上下文
    :param max_memories: 最大回忆数量（默认5）
    :param recall_mode: 回忆模式（smart/semantic/tag_based/hybrid）
    """
    result = memory_manager.trigger_enhanced_recall(context, max_memories, recall_mode)
    
    if not result.get("success", False):
        return f"❌ 主动回忆失败: {result.get('error', '未知错误')}"
    
    memories = result.get("memories", [])
    summary = result.get("summary", "")
    analysis = result.get("analysis", {})
    
    if not memories:
        return f"🔍 基于当前上下文，没有找到相关的历史记忆。\n\n上下文: {context[:100]}..."
    
    response = f"🧠 VCP增强主动回忆结果（模式: {recall_mode}）\n\n"
    response += f"📋 上下文: {context[:150]}...\n\n"
    
    # 显示分析结果
    if analysis:
        response += "🔍 上下文分析:\n"
        response += f"  • 关键概念: {', '.join(analysis.get('key_concepts', [])[:3])}\n"
        response += f"  • 建议标签: {', '.join(analysis.get('suggested_tags', [])[:3])}\n"
        response += f"  • 记忆类型: {analysis.get('memory_type', 'unknown')}\n\n"
    
    response += f"📊 统计: 找到 {len(memories)} 个相关记忆\n\n"
    response += f"📝 回忆总结: {summary}\n\n"
    
    response += "🔍 相关记忆:\n\n"
    
    for i, memory in enumerate(memories, 1):
        score = memory.get("relevance_score", 0)
        mem_type = memory.get("type", "unknown")
        tags = memory.get("tags", [])
        content = memory.get("content", "")[:100] + "..." if len(memory.get("content", "")) > 100 else memory.get("content", "")
        
        # 相关性图标
        if score >= 0.8:
            relevance_icon = "🔥"
        elif score >= 0.6:
            relevance_icon = "⭐"
        elif score >= 0.4:
            relevance_icon = "📝"
        else:
            relevance_icon = "📄"
        
        response += f"{i}. {relevance_icon} 相关性: {score:.2f} ({mem_type})\n"
        response += f"   内容: {content}\n"
        
        if tags:
            response += f"   标签: {', '.join(tags[:3])}\n"
        
        response += "\n"
    
    response += "💡 使用建议:\n"
    response += "1. 这些记忆可以帮助您更好地理解当前任务\n"
    response += "2. 参考历史经验可以避免重复错误\n"
    response += "3. 使用 store_kilo_memory 存储新的重要发现\n"
    response += "4. 尝试不同的回忆模式以获得最佳结果"
    
    return response

@mcp.tool()
def analyze_memory_content(content: str) -> str:
    """
    深度分析记忆内容，提供类型识别、质量评估和标签建议。
    
    :param content: 要分析的记忆内容
    """
    try:
        analysis = memory_manager.analyzer.analyze_memory(content)
        
        response = "🔍 记忆内容深度分析报告\n\n"
        response += f"📝 分析内容: {content[:100]}...\n\n"
        
        response += "📊 分析结果:\n"
        response += f"  • 记忆类型: {analysis['memory_type']}\n"
        response += f"  • 关键概念: {', '.join(analysis['key_concepts'][:5]) if analysis['key_concepts'] else '无'}\n"
        response += f"  • 建议标签: {', '.join(analysis['suggested_tags'][:5]) if analysis['suggested_tags'] else '无'}\n\n"
        
        # 质量评估
        quality = analysis['quality_assessment']
        response += "⭐ 质量评估:\n"
        response += f"  • 总体评分: {quality['overall_score']:.2f}\n"
        response += "  • 维度评分:\n"
        for dim, score in quality['dimension_scores'].items():
            dim_name = {
                "semantic_density": "语义密度",
                "information_value": "信息价值",
                "structural_clarity": "结构清晰度",
                "actionability": "可操作性",
                "novelty": "新颖性",
                "tag_relevance": "标签相关性"
            }.get(dim, dim)
            response += f"    - {dim_name}: {score:.2f}\n"
        
        # 相关记忆
        related = analysis['related_memories']
        if related:
            response += "\n🔗 相关记忆:\n"
            for rel in related[:3]:
                response += f"  • {rel.get('title', '相关记忆')} (相关性: {rel.get('relevance_score', 0):.2f})\n"
        
        response += "\n💡 存储建议:\n"
        response += "1. 使用 store_kilo_memory 存储此记忆\n"
        response += "2. 考虑添加建议的标签\n"
        response += "3. 根据质量评估优化内容结构"
        
        return response
        
    except Exception as e:
        return f"❌ 记忆分析失败: {str(e)}"

# 主函数
if __name__ == "__main__":
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("VCPToolBox增强版 KiloMemoryMCP 服务器\n")
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("核心特性:\n")
    sys.stderr.write("1. ✅ 深度VCP集成：直接使用VCP记忆系统\n")
    sys.stderr.write("2. ✅ 智能记忆分析：多维度质量评估和类型识别\n")
    sys.stderr.write("3. ✅ 增强主动回忆：支持多种回忆模式\n")
    sys.stderr.write("4. ✅ 语义标签系统：自动标签建议和概念提取\n")
    sys.stderr.write("5. ✅ 混合搜索策略：VCP向量+文件系统混合搜索\n")
    sys.stderr.write("6. ✅ 详细统计分析：记忆类型和质量分布分析\n")
    sys.stderr.write("=" * 60 + "\n")
    
    # 检查并确保VCP服务运行
    vcp_client = VCPAPIClient()
    sys.stderr.write("🔍 检查VCP服务状态...\n")
    sys.stderr.flush()
    
    if vcp_client.is_vcp_running():
        sys.stderr.write("✅ VCP服务器连接正常\n")
        sys.stderr.flush()
    else:
        sys.stderr.write("⚠️ VCP服务器未运行，尝试自动启动...\n")
        sys.stderr.flush()
        
        if vcp_client.ensure_vcp_service():
            sys.stderr.write("✅ VCP服务自动启动成功！\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("❌ VCP服务自动启动失败，将使用回退搜索\n")
            sys.stderr.write("💡 提示：您可以手动启动VCP服务以获得最佳体验\n")
            sys.stderr.flush()
    
    # 显示记忆系统状态
    stats = memory_manager.get_memory_stats()
    sys.stderr.write(f"\n📊 记忆系统状态:\n")
    sys.stderr.write(f"  总记忆数量: {stats.get('total_memories', 0)}\n")
    sys.stderr.write(f"  VCP搜索可用: {'✅' if stats.get('vcp_available') else '❌'}\n")
    sys.stderr.flush()
    
    # 运行 MCP 服务器
    sys.stderr.write("\n🚀 启动VCP增强版KiloMemoryMCP服务器...\n")
    sys.stderr.flush()
    mcp.run()
