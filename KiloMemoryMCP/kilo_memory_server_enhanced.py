"""
增强版 KiloMemoryMCP - 具备记忆进化能力的AI Agent记忆系统

核心特性：
1. 记忆存储与向量索引集成
2. 记忆关联分析与知识图谱构建
3. 记忆重要性评估与质量评分
4. 记忆融合与抽象能力
5. 智能遗忘与记忆优化
6. 记忆进化跟踪与可视化

架构设计：
- 底层：文件存储 + SQLite数据库 + 向量索引
- 中层：记忆处理器 + 关联分析器 + 质量评估器
- 上层：记忆进化引擎 + 知识图谱构建器
"""

import os
import sys
import json
import sqlite3
import datetime
import subprocess
import socket
import threading
import time
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from mcp.server.fastmcp import FastMCP

# 设置标准输出编码为UTF-8，避免Windows下的编码错误
if sys.platform == "win32":
    try:
        # 尝试设置控制台编码为UTF-8
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 导入改进的回忆系统
try:
    from improved_recall_system import (
        ProactiveRecallEngine, 
        NaturalRecallIntegrator,
        setup_enhanced_recall_system
    )
    IMPROVED_RECALL_AVAILABLE = True
except ImportError:
    IMPROVED_RECALL_AVAILABLE = False
    print("警告: 改进的回忆系统不可用，将使用基础查询功能")

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_Enhanced")

# 路径配置
PROJECT_ROOT = r"d:/vscode/AgentV"
MEMORY_DIR = os.path.join(PROJECT_ROOT, "dailynote", "KiloMemory")
DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "knowledge_base.sqlite")
EVOLUTION_DB_PATH = os.path.join(PROJECT_ROOT, "VectorStore", "memory_evolution.sqlite")
VCP_PORT = 6005  # 默认 VCP 端口

# 记忆类型枚举
class MemoryType(Enum):
    FACT = "fact"           # 事实性记忆
    EXPERIENCE = "experience" # 经验性记忆
    SKILL = "skill"         # 技能性记忆
    INSIGHT = "insight"     # 洞察性记忆
    REFLECTION = "reflection" # 反思性记忆
    PLAN = "plan"           # 计划性记忆

# 记忆质量评分
@dataclass
class MemoryQuality:
    relevance: float = 0.0      # 相关性 (0-1)
    clarity: float = 0.0        # 清晰度 (0-1)
    completeness: float = 0.0   # 完整性 (0-1)
    importance: float = 0.0     # 重要性 (0-1)
    novelty: float = 0.0        # 新颖性 (0-1)
    
    @property
    def overall_score(self) -> float:
        """综合质量评分"""
        weights = {
            'relevance': 0.25,
            'clarity': 0.20,
            'completeness': 0.15,
            'importance': 0.25,
            'novelty': 0.15
        }
        return sum(getattr(self, attr) * weight for attr, weight in weights.items())

# 记忆元数据
@dataclass
class MemoryMetadata:
    memory_id: str
    timestamp: str
    memory_type: MemoryType
    quality: MemoryQuality
    access_count: int = 0
    last_accessed: Optional[str] = None
    related_memories: List[str] = None
    abstraction_level: int = 0  # 0=具体, 1=抽象, 2=高度抽象
    
    def __post_init__(self):
        if self.related_memories is None:
            self.related_memories = []

# 记忆进化跟踪器
class MemoryEvolutionTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_evolution_db()
    
    def _init_evolution_db(self):
        """初始化记忆进化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记忆进化表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL,
                parent_id TEXT,
                evolution_type TEXT NOT NULL,
                evolution_stage INTEGER DEFAULT 0,
                quality_before TEXT,
                quality_after TEXT,
                change_reason TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # 记忆关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                discovered_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0
            )
        """)
        
        # 记忆质量历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_quality_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL,
                quality_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                reason TEXT
            )
        """)
        
        # 知识图谱节点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                centrality REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 知识图谱边表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def track_evolution(self, memory_id: str, evolution_type: str, 
                       quality_before: Optional[MemoryQuality] = None,
                       quality_after: Optional[MemoryQuality] = None,
                       change_reason: str = "",
                       metadata: Dict = None):
        """跟踪记忆进化过程"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取当前进化阶段
        cursor.execute(
            "SELECT MAX(evolution_stage) FROM memory_evolution WHERE memory_id = ?",
            (memory_id,)
        )
        result = cursor.fetchone()
        next_stage = (result[0] or 0) + 1 if result else 1
        
        cursor.execute("""
            INSERT INTO memory_evolution 
            (memory_id, evolution_type, evolution_stage, quality_before, 
             quality_after, change_reason, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            evolution_type,
            next_stage,
            json.dumps(asdict(quality_before)) if quality_before else None,
            json.dumps(asdict(quality_after)) if quality_after else None,
            change_reason,
            datetime.datetime.now().isoformat(),
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def add_relation(self, source_id: str, target_id: str, 
                    relation_type: str, strength: float = 1.0):
        """添加记忆关联"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM memory_relations 
            WHERE source_id = ? AND target_id = ? AND relation_type = ?
        """, (source_id, target_id, relation_type))
        
        if cursor.fetchone():
            # 更新强度
            cursor.execute("""
                UPDATE memory_relations 
                SET strength = ?, last_accessed = ?
                WHERE source_id = ? AND target_id = ? AND relation_type = ?
            """, (
                strength,
                datetime.datetime.now().isoformat(),
                source_id, target_id, relation_type
            ))
        else:
            # 新建关联
            cursor.execute("""
                INSERT INTO memory_relations 
                (source_id, target_id, relation_type, strength, discovered_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                source_id,
                target_id,
                relation_type,
                strength,
                datetime.datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def record_quality_change(self, memory_id: str, quality_score: float, 
                             reason: str = ""):
        """记录记忆质量变化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memory_quality_history 
            (memory_id, quality_score, timestamp, reason)
            VALUES (?, ?, ?, ?)
        """, (
            memory_id,
            quality_score,
            datetime.datetime.now().isoformat(),
            reason
        ))
        
        conn.commit()
        conn.close()

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
        """分析记忆类型"""
        content_lower = content.lower()
        
        # 基于关键词的模式匹配
        type_scores = {mem_type: 0 for mem_type in MemoryType}
        
        for mem_type, pattern in self.keyword_patterns.items():
            matches = re.findall(pattern, content_lower)
            type_scores[MemoryType(mem_type)] = len(matches)
        
        # 基于内容结构的判断
        if re.search(r'\d+\.\s|\-\s|\*\s', content):  # 列表格式
            type_scores[MemoryType.SKILL] += 2
        if re.search(r'应该|建议|最好', content):  # 建议性内容
            type_scores[MemoryType.INSIGHT] += 1
        
        # 返回得分最高的类型
        return max(type_scores.items(), key=lambda x: x[1])[0]
    
    def assess_memory_quality(self, content: str, tags: List[str]) -> MemoryQuality:
        """评估记忆质量"""
        quality = MemoryQuality()
        
        # 1. 相关性评估（基于标签数量和质量）
        if tags:
            quality.relevance = min(1.0, len(tags) / 10)  # 最多10个标签
        
        # 2. 清晰度评估（基于句子结构和长度）
        sentences = re.split(r'[。！？.!?]', content)
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        
        if 10 <= avg_sentence_length <= 50:
            quality.clarity = 0.8
        elif avg_sentence_length < 10:
            quality.clarity = 0.5
        else:
            quality.clarity = 0.6
        
        # 3. 完整性评估（基于内容长度和结构）
        content_length = len(content)
        if content_length > 500:
            quality.completeness = 0.9
        elif content_length > 200:
            quality.completeness = 0.7
        elif content_length > 50:
            quality.completeness = 0.5
        else:
            quality.completeness = 0.3
        
        # 4. 重要性评估（基于关键词和特殊标记）
        important_keywords = ['重要', '关键', '核心', '必须', '必要', 'essential', 'critical']
        has_important = any(keyword in content for keyword in important_keywords)
        quality.importance = 0.8 if has_important else 0.5
        
        # 5. 新颖性评估（基于时间戳和内容独特性）
        # 这里简化处理，实际应该与已有记忆对比
        quality.novelty = 0.7  # 默认值
        
        return quality
    
    def extract_key_concepts(self, content: str) -> List[str]:
        """提取关键概念"""
        # 简单的概念提取：名词短语、专业术语等
        concepts = []
        
        # 提取括号内的内容
        concepts.extend(re.findall(r'【(.*?)】|\((.*?)\)|（(.*?)）', content))
        
        # 提取引号内的内容
        concepts.extend(re.findall(r'["\'](.*?)["\']', content))
        
        # 提取大写字母开头的连续词（可能为专有名词）
        concepts.extend(re.findall(r'\b[A-Z][a-z]+\b', content))
        
        # 清理和去重
        concepts = [c for sublist in concepts for c in sublist if c]
        concepts = list(set(concepts))
        
        return concepts

# 记忆融合器
class MemoryFusionEngine:
    def __init__(self, tracker: MemoryEvolutionTracker):
        self.tracker = tracker
    
    def find_similar_memories(self, memory_id: str, content: str, 
                             limit: int = 5) -> List[Tuple[str, float]]:
        """查找相似记忆（简化版，实际应使用向量搜索）"""
        # 这里应该调用KnowledgeBaseManager的向量搜索
        # 暂时返回空列表
        return []
    
    def fuse_memories(self, memory_ids: List[str], new_content: str) -> Dict:
        """融合多个记忆"""
        # 记忆融合逻辑
        fused_memory = {
            'content': new_content,
            'sources': memory_ids,
            'fusion_type': 'consolidation',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # 跟踪融合过程
        for mem_id in memory_ids:
            self.tracker.track_evolution(
                mem_id,
                'fusion',
                change_reason=f"融合到新记忆，包含{len(memory_ids)}个源记忆"
            )
        
        return fused_memory
    
    def abstract_memory(self, memory_id: str, content: str, 
                       abstraction_level: int = 1) -> str:
        """抽象记忆内容"""
        # 简化版抽象：提取关键句和总结
        sentences = re.split(r'[。！？.!?]', content)
        
        if abstraction_level == 1:
            # 一级抽象：取首尾句
            if len(sentences) >= 3:
                abstracted = sentences[0] + "。" + sentences[-1] + "。"
            else:
                abstracted = content
        elif abstraction_level == 2:
            # 二级抽象：提取关键词和核心意思
            keywords = self._extract_keywords(content)
            abstracted = f"核心概念：{', '.join(keywords[:5])}"
        else:
            abstracted = content
        
        return abstracted
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 移除停用词
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        words = re.findall(r'[\u4e00-\u9fa5]+|[A-Za-z]+', text)
        return [w for w in words if w not in stopwords][:10]

# 主记忆管理器
class EnhancedMemoryManager:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.db_path = DB_PATH
        self.evolution_tracker = MemoryEvolutionTracker(EVOLUTION_DB_PATH)
        self.analyzer = MemoryAnalyzer()
        self.fusion_engine = MemoryFusionEngine(self.evolution_tracker)
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录存在"""
        os.makedirs(self.memory_dir, exist_ok=True)
        os.makedirs(os.path.dirname(EVOLUTION_DB_PATH), exist_ok=True)
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if not os.path.exists(self.db_path):
            return None
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_memory_id(self, content: str) -> str:
        """生成记忆ID（基于内容哈希）"""
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        return f"mem_{timestamp}_{content_hash}"
    
    def store_memory(self, content: str, tags: List[str] = None, 
                    metadata: Dict = None) -> Dict:
        """存储增强记忆"""
        try:
            # 生成记忆ID
            memory_id = self.generate_memory_id(content)
            
            # 分析记忆
            memory_type = self.analyzer.analyze_memory_type(content)
            quality = self.analyzer.assess_memory_quality(content, tags or [])
            key_concepts = self.analyzer.extract_key_concepts(content)
            
            # 创建记忆文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"memory_{timestamp}_{memory_id}.md"
            filepath = os.path.join(self.memory_dir, filename)
            
            # 构建增强的Markdown内容
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

### 进化跟踪
- 创建时间: {datetime.datetime.now().isoformat()}
- 记忆哈希: {hashlib.md5(content.encode()).hexdigest()[:8]}

Tag: {tag_str}
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            # 跟踪记忆创建
            self.evolution_tracker.track_evolution(
                memory_id,
                "creation",
                quality_after=quality,
                change_reason="新记忆创建",
                metadata={
                    "type": memory_type.value,
                    "filepath": filepath,
                    "tags": tags or [],
                    "concepts": key_concepts
                }
            )
            
            # 记录初始质量
            self.evolution_tracker.record_quality_change(
                memory_id,
                quality.overall_score,
                "初始创建"
            )
            
            # 查找并建立相似记忆关联
            similar_memories = self.fusion_engine.find_similar_memories(
                memory_id, content
            )
            
            for similar_id, similarity in similar_memories:
                if similarity > 0.7:  # 相似度阈值
                    self.evolution_tracker.add_relation(
                        memory_id,
                        similar_id,
                        "similar",
                        similarity
                    )
            
            return {
                "success": True,
                "memory_id": memory_id,
                "filepath": filepath,
                "metadata": {
                    "type": memory_type.value,
                    "quality": asdict(quality),
                    "concepts": key_concepts,
                    "similar_memories_found": len(similar_memories)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_memories(self, query: str = "", limit: int = 10, 
                      min_quality: float = 0.0) -> List[Dict]:
        """查询记忆（增强版）"""
        try:
            results = []
            
            # 1. 首先尝试从向量数据库查询
            conn = self._get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                # 查询KiloMemory相关的记忆块
                sql = """
                    SELECT c.content, f.path, f.updated_at 
                    FROM chunks c 
                    JOIN files f ON c.file_id = f.id 
                    WHERE f.diary_name = 'KiloMemory' 
                    AND c.content LIKE ? 
                    ORDER BY f.updated_at DESC 
                    LIMIT ?
                """
                cursor.execute(sql, (f"%{query}%", limit * 2))  # 多查一些用于过滤
                rows = cursor.fetchall()
                
                for row in rows:
                    content = row['content']
                    
                    # 评估质量
                    quality = self.analyzer.assess_memory_quality(content, [])
                    
                    if quality.overall_score >= min_quality:
                        results.append({
                            "content": content,
                            "source": row['path'],
                            "time": datetime.datetime.fromtimestamp(
                                row['updated_at']
                            ).isoformat() if row['updated_at'] else "unknown",
                            "quality_score": quality.overall_score,
                            "type": self.analyzer.analyze_memory_type(content).value
                        })
                
                conn.close()
            
            # 2. 如果数据库结果不足，从文件系统补充
            if len(results) < limit:
                ensure_memory_dir()
                files = [f for f in os.listdir(self.memory_dir) 
                        if f.endswith(".md")]
                files.sort(reverse=True)
                
                for fname in files:
                    if len(results) >= limit:
                        break
                    
                    fpath = os.path.join(self.memory_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        if query.lower() in content.lower():
                            quality = self.analyzer.assess_memory_quality(content, [])
                            
                            if quality.overall_score >= min_quality:
                                results.append({
                                    "file": fname,
                                    "content": content[:500] + "..." 
                                             if len(content) > 500 else content,
                                    "quality_score": quality.overall_score,
                                    "type": self.analyzer.analyze_memory_type(content).value
                                })
            
            # 按质量评分排序
            results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            return [{"error": f"查询失败: {str(e)}"}]
    
    def evolve_memory(self, memory_id: str, evolution_type: str, 
                     new_content: str = None) -> Dict:
        """进化记忆"""
        try:
            # 查找原始记忆文件
            memory_files = [f for f in os.listdir(self.memory_dir) 
                          if memory_id in f and f.endswith(".md")]
            
            if not memory_files:
                return {"success": False, "error": "记忆未找到"}
            
            original_file = os.path.join(self.memory_dir, memory_files[0])
            
            with open(original_file, "r", encoding="utf-8") as f:
                original_content = f.read()
            
            # 分析原始质量
            original_quality = self.analyzer.assess_memory_quality(
                original_content, []
            )
            
            # 根据进化类型处理
            if evolution_type == "abstract":
                # 抽象化
                abstraction_level = 1
                evolved_content = self.fusion_engine.abstract_memory(
                    memory_id, original_content, abstraction_level
                )
                change_reason = f"抽象化到级别{abstraction_level}"
                
            elif evolution_type == "refine" and new_content:
                # 精炼
                evolved_content = new_content
                change_reason = "内容精炼"
                
            elif evolution_type == "merge":
                # 需要指定要合并的记忆ID
                change_reason = "记忆融合"
                return {
                    "success": False,
                    "error": "合并功能需要指定要合并的记忆ID列表",
                    "suggestion": "使用fuse_memories方法"
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的进化类型: {evolution_type}"
                }
            
            # 评估进化后质量
            evolved_quality = self.analyzer.assess_memory_quality(
                evolved_content, []
            )
            
            # 创建进化版本文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            evolved_filename = f"memory_{timestamp}_{memory_id}_evolved.md"
            evolved_filepath = os.path.join(self.memory_dir, evolved_filename)
            
            with open(evolved_filepath, "w", encoding="utf-8") as f:
                f.write(evolved_content)
            
            # 跟踪进化过程
            self.evolution_tracker.track_evolution(
                memory_id,
                evolution_type,
                original_quality,
                evolved_quality,
                change_reason,
                {
                    "original_file": original_file,
                    "evolved_file": evolved_filepath,
                    "abstraction_level": 1 if evolution_type == "abstract" else 0
                }
            )
            
            # 记录质量变化
            self.evolution_tracker.record_quality_change(
                memory_id,
                evolved_quality.overall_score,
                f"{evolution_type}进化"
            )
            
            return {
                "success": True,
                "memory_id": memory_id,
                "evolution_type": evolution_type,
                "original_quality": original_quality.overall_score,
                "evolved_quality": evolved_quality.overall_score,
                "improvement": evolved_quality.overall_score - original_quality.overall_score,
                "evolved_file": evolved_filepath
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_memory_evolution_history(self, memory_id: str) -> List[Dict]:
        """获取记忆进化历史"""
        try:
            conn = sqlite3.connect(EVOLUTION_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM memory_evolution 
                WHERE memory_id = ? 
                ORDER BY evolution_stage ASC
            """, (memory_id,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "evolution_stage": row['evolution_stage'],
                    "evolution_type": row['evolution_type'],
                    "timestamp": row['timestamp'],
                    "change_reason": row['change_reason'],
                    "quality_before": json.loads(row['quality_before']) 
                                    if row['quality_before'] else None,
                    "quality_after": json.loads(row['quality_after']) 
                                   if row['quality_after'] else None,
                    "metadata": json.loads(row['metadata']) 
                               if row['metadata'] else None
                })
            
            conn.close()
            return history
            
        except Exception as e:
            return [{"error": f"获取历史失败: {str(e)}"}]
    
    def analyze_memory_network(self, depth: int = 2) -> Dict:
        """分析记忆网络"""
        try:
            conn = sqlite3.connect(EVOLUTION_DB_PATH)
            cursor = conn.cursor()
            
            # 获取记忆关系
            cursor.execute("""
                SELECT source_id, target_id, relation_type, strength 
                FROM memory_relations 
                ORDER BY strength DESC
            """)
            
            relations = []
            for row in cursor.fetchall():
                relations.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                    "strength": row[3]
                })
            
            # 统计记忆类型分布
            memory_files = [f for f in os.listdir(self.memory_dir) 
                          if f.endswith(".md")]
            
            type_distribution = {}
            for fname in memory_files[:50]:  # 采样分析
                fpath = os.path.join(self.memory_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    mem_type = self.analyzer.analyze_memory_type(content)
                    type_distribution[mem_type.value] = \
                        type_distribution.get(mem_type.value, 0) + 1
            
            conn.close()
            
            return {
                "total_memories": len(memory_files),
                "total_relations": len(relations),
                "relation_types": list(set(r["type"] for r in relations)),
                "type_distribution": type_distribution,
                "sample_relations": relations[:10]  # 返回前10个关系作为样本
            }
            
        except Exception as e:
            return {"error": f"网络分析失败: {str(e)}"}

# 工具函数（保持与原始MCP兼容）
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

# 初始化记忆管理器
memory_manager = EnhancedMemoryManager()

# 初始化改进的回忆系统（如果可用）
if IMPROVED_RECALL_AVAILABLE:
    try:
        recall_system = setup_enhanced_recall_system(memory_manager)
        recall_engine = recall_system["recall_engine"]
        recall_integrator = recall_system["integrator"]
        print("✅ 改进的回忆系统已初始化")
    except Exception as e:
        print(f"⚠️ 改进的回忆系统初始化失败: {e}")
        recall_engine = None
        recall_integrator = None
else:
    recall_engine = None
    recall_integrator = None

# MCP工具定义
@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 dailynote 文件夹（增强版）。
    这些记忆会被项目的 KnowledgeBaseManager 自动扫描并建立向量索引。
    新增记忆进化跟踪和质量评估功能。
    :param content: 记忆内容
    :param tags: 标签列表
    """
    result = memory_manager.store_memory(content, tags)
    
    if result["success"]:
        memory_id = result["memory_id"]
        metadata = result["metadata"]
        
        # 安全地获取质量评分
        quality_dict = metadata.get('quality', {})
        quality_score = quality_dict.get('overall_score', 0.0)
        if not quality_score and 'overall_score' not in quality_dict:
            # 如果字典中没有overall_score，尝试计算
            try:
                from dataclasses import asdict
                quality_obj = MemoryQuality(**quality_dict)
                quality_score = quality_obj.overall_score
            except:
                quality_score = 0.0
        
        response = f"""✅ 记忆存储成功（增强版）！

记忆ID: {memory_id}
存储位置: {result['filepath']}
记忆类型: {metadata['type']}
质量评分: {quality_score:.2f}
关键概念: {', '.join(metadata['concepts'][:5]) if metadata['concepts'] else '无'}
发现相似记忆: {metadata['similar_memories_found']}个

该记忆已进入进化跟踪系统，将被KnowledgeBaseManager自动索引。"""
        
        return response
    else:
        return f"❌ 记忆存储失败: {result['error']}"

@mcp.tool()
def query_kilo_memory(query: str = "", limit: int = 10, 
                     min_quality: float = 0.0) -> str:
    """
    查询 Kilo Code 的记忆（增强版）。
    新增质量过滤和记忆类型识别功能。
    集成改进的回忆系统，支持上下文感知和主动回忆。
    :param query: 查询关键词
    :param limit: 返回数量限制
    :param min_quality: 最低质量评分（0-1）
    """
    # 如果启用了改进的回忆系统，使用主动回忆
    if recall_engine and query:
        # 分析上下文，判断是否需要主动回忆
        should_recall, recall_info = recall_engine.should_recall(query)
        
        if should_recall:
            # 执行主动回忆
            recall_results = recall_engine.execute_recall(recall_info["context"])
            
            if recall_results.get("success") and recall_results.get("results"):
                # 获取自然集成的结果
                natural_response = recall_integrator.integrate_recall(recall_results) if recall_integrator else ""
                
                # 获取详细结果用于显示
                enhanced_results = recall_results["results"]
                
                # 构建响应
                response = f"🧠 主动回忆起相关记忆（基于上下文分析）:\n\n"
                
                if natural_response:
                    response += f"{natural_response}\n\n"
                
                response += f"🔍 详细结果（共找到 {len(enhanced_results)} 条相关记忆）:\n\n"
                
                for i, mem in enumerate(enhanced_results[:limit], 1):
                    quality = mem.get("quality_score", 0)
                    relevance = mem.get("relevance_score", 0)
                    mem_type = mem.get("type", "unknown")
                    
                    response += f"{i}. 【{mem_type}】质量:{quality:.2f} | 相关性:{relevance:.2f}\n"
                    
                    if "content" in mem:
                        content_preview = mem["content"][:150] + "..." \
                                        if len(mem["content"]) > 150 else mem["content"]
                        response += f"   {content_preview}\n"
                    
                    response += "\n"
                
                return response
    
    # 如果未触发主动回忆或主动回忆失败，使用基础查询
    results = memory_manager.query_memories(query, limit, min_quality)
    
    if not results or ("error" in results[0]):
        return "未找到匹配的记忆。" if not results else f"查询失败: {results[0]['error']}"
    
    response = f"🔍 找到 {len(results)} 条相关记忆（质量≥{min_quality}）:\n\n"
    
    for i, mem in enumerate(results, 1):
        quality = mem.get("quality_score", 0)
        mem_type = mem.get("type", "unknown")
        
        response += f"{i}. 【{mem_type}】质量:{quality:.2f}\n"
        
        if "content" in mem:
            content_preview = mem["content"][:200] + "..." \
                            if len(mem["content"]) > 200 else mem["content"]
            response += f"   {content_preview}\n"
        
        if "time" in mem and mem["time"] != "unknown":
            response += f"   时间: {mem['time']}\n"
        
        response += "\n"
    
    return response

@mcp.tool()
def evolve_memory(memory_id: str, evolution_type: str, 
                 new_content: str = None) -> str:
    """
    进化记忆：抽象化、精炼或融合记忆。
    :param memory_id: 记忆ID（格式：mem_YYYYMMDD_xxxxxx）
    :param evolution_type: 进化类型（abstract/refine/merge）
    :param new_content: 精炼时的新内容（仅refine类型需要）
    """
    result = memory_manager.evolve_memory(memory_id, evolution_type, new_content)
    
    if result["success"]:
        return f"""🧬 记忆进化成功！

记忆ID: {result['memory_id']}
进化类型: {result['evolution_type']}
质量变化: {result['original_quality']:.2f} → {result['evolved_quality']:.2f}
改进幅度: {result['improvement']:+.2f}
进化文件: {result['evolved_file']}

进化历史已记录到记忆进化数据库。"""
    else:
        return f"❌ 记忆进化失败: {result['error']}"

@mcp.tool()
def get_memory_evolution_history(memory_id: str) -> str:
    """
    获取记忆的进化历史。
    :param memory_id: 记忆ID
    """
    history = memory_manager.get_memory_evolution_history(memory_id)
    
    if not history or ("error" in history[0]):
        return f"记忆 {memory_id} 没有进化历史记录。" \
               if not history else f"获取历史失败: {history[0]['error']}"
    
    response = f"📜 记忆 {memory_id} 的进化历史（共{len(history)}个阶段）:\n\n"
    
    for i, stage in enumerate(history, 1):
        response += f"阶段 {stage['evolution_stage']}: {stage['evolution_type']}\n"
        response += f"  时间: {stage['timestamp']}\n"
        response += f"  原因: {stage['change_reason']}\n"
        
        if stage['quality_before'] and stage['quality_after']:
            before = stage['quality_before']['overall_score']
            after = stage['quality_after']['overall_score']
            response += f"  质量变化: {before:.2f} → {after:.2f} ({after-before:+.2f})\n"
        
        response += "\n"
    
    return response

@mcp.tool()
def analyze_memory_network() -> str:
    """
    分析记忆网络，展示记忆之间的关系和类型分布。
    """
    analysis = memory_manager.analyze_memory_network()
    
    if "error" in analysis:
        return f"网络分析失败: {analysis['error']}"
    
    response = "🕸️ 记忆网络分析报告\n\n"
    response += f"总记忆数量: {analysis['total_memories']}\n"
    response += f"总关系数量: {analysis['total_relations']}\n"
    response += f"关系类型: {', '.join(analysis['relation_types'])}\n\n"
    
    response += "记忆类型分布:\n"
    for mem_type, count in analysis['type_distribution'].items():
        percentage = (count / analysis['total_memories'] * 100) \
                    if analysis['total_memories'] > 0 else 0
        response += f"  {mem_type}: {count} ({percentage:.1f}%)\n"
    
    response += "\n代表性关系（前10个）:\n"
    for i, rel in enumerate(analysis.get('sample_relations', []), 1):
        response += f"  {i}. {rel['source']} → {rel['target']} " \
                   f"[{rel['type']}, 强度:{rel['strength']:.2f}]\n"
    
    return response

@mcp.tool()
def list_all_kilo_memories(limit: int = 20) -> str:
    """
    列出最近的 Kilo Code 记忆（增强版）。
    :param limit: 返回数量限制
    """
    return query_kilo_memory("", limit)

@mcp.tool()
def get_memory_insights() -> str:
    """
    获取记忆系统的洞察分析。
    """
    try:
        # 分析记忆质量趋势
        conn = sqlite3.connect(EVOLUTION_DB_PATH)
        cursor = conn.cursor()
        
        # 获取质量历史
        cursor.execute("""
            SELECT memory_id, quality_score, timestamp 
            FROM memory_quality_history 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        
        quality_history = []
        for row in cursor.fetchall():
            quality_history.append({
                "memory_id": row[0],
                "quality": row[1],
                "time": row[2]
            })
        
        # 计算平均质量
        avg_quality = sum(h["quality"] for h in quality_history) / \
                     len(quality_history) if quality_history else 0
        
        # 获取进化统计
        cursor.execute("""
            SELECT evolution_type, COUNT(*) as count 
            FROM memory_evolution 
            GROUP BY evolution_type
        """)
        
        evolution_stats = {}
        for row in cursor.fetchall():
            evolution_stats[row[0]] = row[1]
        
        conn.close()
        
        # 分析文件系统
        memory_files = [f for f in os.listdir(MEMORY_DIR) 
                       if f.endswith(".md")]
        
        # 按时间分析
        recent_count = 0
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        for fname in memory_files:
            try:
                file_time_str = fname.split("_")[1]  # memory_YYYYMMDD_...
                file_date = datetime.datetime.strptime(file_time_str[:8], "%Y%m%d")
                if file_date > week_ago:
                    recent_count += 1
            except:
                continue
        
        response = "🧠 记忆系统洞察报告\n\n"
        response += f"📊 系统统计:\n"
        response += f"  总记忆文件: {len(memory_files)}\n"
        response += f"  最近7天新增: {recent_count}\n"
        response += f"  平均质量评分: {avg_quality:.2f}/1.0\n\n"
        
        response += f"🔄 进化活动:\n"
        for evo_type, count in evolution_stats.items():
            response += f"  {evo_type}: {count}次\n"
        
        response += f"\n💡 建议:\n"
        if avg_quality < 0.6:
            response += "  记忆质量偏低，建议加强记忆的精炼和抽象化。\n"
        if recent_count < 5:
            response += "  近期记忆创建较少，建议增加记忆记录频率。\n"
        if len(evolution_stats) == 0:
            response += "  尚未进行记忆进化，尝试使用evolve_memory工具。\n"
        else:
            response += "  记忆进化活跃，系统正在持续优化。\n"
        
        return response
        
    except Exception as e:
        return f"洞察分析失败: {str(e)}"

def test_enhanced_query():
    """测试改进的query_kilo_memory功能"""
    print("\n" + "=" * 60)
    print("测试改进的query_kilo_memory功能")
    print("=" * 60)
    
    test_queries = [
        "电脑硬件环境",
        "系统配置",
        "ROG Strix",
        "Windows 11",
        "回忆我的电脑配置"
    ]
    
    for query in test_queries:
        print(f"\n测试查询: '{query}'")
        result = query_kilo_memory(query, limit=3)
        try:
            # 安全地打印结果，避免编码错误
            if len(result) > 200:
                preview = result[:200]
                # 移除可能引起编码问题的Unicode字符
                preview = preview.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(f"结果预览: {preview}...")
            else:
                safe_result = result.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(f"结果: {safe_result}")
        except Exception as e:
            print(f"打印结果时出错: {e}")
            print(f"结果长度: {len(result)} 字符")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

# 主函数
if __name__ == "__main__":
    # 启动时尝试静默启动 VCP 后端
    threading.Thread(target=start_vcp_backend, daemon=True).start()
    
    print("=" * 60)
    print("增强版 KiloMemoryMCP 启动（集成改进回忆系统）")
    print("=" * 60)
    print("核心特性:")
    print("1. 记忆类型自动识别（事实/经验/技能/洞察/反思/计划）")
    print("2. 记忆质量多维评估（相关性/清晰度/完整性/重要性/新颖性）")
    print("3. 记忆进化跟踪（抽象化/精炼/融合）")
    print("4. 记忆关联分析与知识图谱构建")
    print("5. 智能记忆网络分析与洞察报告")
    print("6. 改进的回忆系统（一次回忆起/主动回忆起/自然回忆起）")
    print("=" * 60)
    
    # 运行测试
    test_enhanced_query()
    
    # 运行 MCP 服务器
    mcp.run()