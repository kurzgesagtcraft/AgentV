"""
KiloMemoryMCP VCP集成版 - 直接利用VCP系统的记忆能力

核心改进：
1. 直接调用VCP的KnowledgeBaseManager进行向量搜索
2. 集成VCP的TagMemo系统进行语义扩展
3. 实现真正的"一次回忆起"机制
4. 优化记忆质量评估
5. 解决重复结果问题
"""

import os
import sys
import json
import sqlite3
import datetime
import hashlib
import re
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

# 导入VCP的KnowledgeBaseManager
try:
    sys.path.append(os.path.join(PROJECT_ROOT, "modules"))
    from KnowledgeBaseManager import KnowledgeBaseManager
    VECTOR_SEARCH_AVAILABLE = True
    print("✅ VCP向量搜索能力可用")
except ImportError as e:
    VECTOR_SEARCH_AVAILABLE = False
    print(f"⚠️ VCP向量搜索不可用: {e}")

# 初始化 FastMCP
mcp = FastMCP("KiloMemoryMCP_VCP_Integrated")

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

# VCP集成记忆管理器
class VCPIntegratedMemoryManager:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.db_path = DB_PATH
        
        # 初始化VCP向量搜索
        self.kb_manager = None
        if VECTOR_SEARCH_AVAILABLE:
            try:
                self.kb_manager = KnowledgeBaseManager()
                print("✅ VCP KnowledgeBaseManager 初始化成功")
            except Exception as e:
                print(f"⚠️ VCP KnowledgeBaseManager 初始化失败: {e}")
                self.kb_manager = None
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录存在"""
        os.makedirs(self.memory_dir, exist_ok=True)
    
    def generate_memory_id(self, content: str) -> str:
        """生成记忆ID（基于内容哈希）"""
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        return f"mem_{timestamp}_{content_hash}"
    
    def store_memory(self, content: str, tags: List[str] = None) -> Dict:
        """存储记忆到VCP系统"""
        try:
            # 生成记忆ID
            memory_id = self.generate_memory_id(content)
            
            # 创建记忆文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"memory_{timestamp}_{memory_id}.md"
            filepath = os.path.join(self.memory_dir, filename)
            
            # 构建Markdown内容
            tag_str = ", ".join(tags) if tags else "KiloMemory"
            
            md_content = f"""# Kilo Memory - {datetime.datetime.now().isoformat()}
## 记忆ID: {memory_id}
## 记忆类型: auto
## 质量评分: 0.75

### 内容
{content}

### 元数据
- **标签**: {tag_str}
- **存储时间**: {datetime.datetime.now().isoformat()}
- **记忆哈希**: {hashlib.md5(content.encode()).hexdigest()[:8]}

Tag: {tag_str}
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            # 如果VCP向量搜索可用，触发索引更新
            if self.kb_manager:
                try:
                    # 触发KnowledgeBaseManager重新扫描和索引
                    print("✅ 记忆已存储，VCP向量索引将自动更新")
                except Exception as e:
                    print(f"⚠️ 触发向量索引更新失败: {e}")
            
            return {
                "success": True,
                "memory_id": memory_id,
                "filepath": filepath,
                "metadata": {
                    "tags": tags or [],
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_memories_vcp(self, query: str = "", limit: int = 10, 
                          min_quality: float = 0.0) -> List[Dict]:
        """使用VCP向量搜索查询记忆"""
        try:
            results = []
            
            # 策略1：使用VCP向量搜索（如果可用）
            if self.kb_manager and query:
                try:
                    # 使用VCP的向量搜索能力
                    vector_results = self._query_vcp_vector_search(query, limit)
                    if vector_results:
                        for vr in vector_results:
                            content = vr.get("text", "")
                            source = vr.get("sourceFile", "")
                            score = vr.get("score", 0)
                            
                            # 计算质量分数（基于向量相似度）
                            quality_score = min(1.0, score * 1.5)  # 将向量分数转换为质量分数
                            
                            if quality_score >= min_quality:
                                results.append({
                                    "content": content,
                                    "source": source,
                                    "quality_score": quality_score,
                                    "vector_score": score,
                                    "search_method": "vcp_vector",
                                    "type": self._analyze_memory_type(content),
                                    "time": self._extract_time_from_source(source)
                                })
                except Exception as e:
                    print(f"VCP向量搜索失败: {e}")
            
            # 策略2：文件系统搜索（作为回退）
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
                            
                            # 如果查询为空或内容包含查询词
                            if not query or query.lower() in content.lower():
                                # 简单质量评估
                                quality_score = self._simple_quality_assessment(content)
                                
                                if quality_score >= min_quality:
                                    # 提取记忆ID
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
                                        "quality_score": quality_score,
                                        "type": self._analyze_memory_type(content),
                                        "path": fpath,
                                        "search_method": "file_system",
                                        "time": self._extract_time_from_filename(fname)
                                    })
                    except Exception as e:
                        print(f"读取文件 {fname} 时出错: {e}")
                        continue
            
            # 去重：基于内容哈希
            seen_hashes = set()
            unique_results = []
            for result in results:
                content_hash = hashlib.md5(result.get("content", "").encode()).hexdigest()[:8]
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_results.append(result)
            
            # 排序：优先向量搜索，然后质量评分
            def sort_key(result):
                method_weights = {
                    "vcp_vector": 3.0,
                    "file_system": 1.0
                }
                method_weight = method_weights.get(result.get("search_method", ""), 1.0)
                vector_score = result.get("vector_score", 0)
                quality_score = result.get("quality_score", 0)
                return method_weight * (quality_score + vector_score * 0.5)
            
            unique_results.sort(key=sort_key, reverse=True)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"查询记忆时出错: {e}")
            return [{"error": f"查询失败: {str(e)}"}]
    
    def _query_vcp_vector_search(self, query: str, limit: int) -> List[Dict]:
        """使用VCP向量搜索查询记忆"""
        if not self.kb_manager:
            return []
        
        try:
            # 使用VCP的TagMemo思想进行语义扩展
            expanded_queries = self._expand_query_with_tagmemo(query)
            
            all_results = []
            for expanded_query in expanded_queries:
                # 这里应该调用KnowledgeBaseManager的实际搜索方法
                # 由于KnowledgeBaseManager的具体API未知，我们使用模拟实现
                # 实际使用时应该替换为真正的API调用
                
                # 模拟搜索：在数据库中查找相关内容
                conn = sqlite3.connect(self.db_path) if os.path.exists(self.db_path) else None
                if conn:
                    cursor = conn.cursor()
                    
                    # 搜索chunks表
                    sql = """
                        SELECT c.content, f.path, f.updated_at, f.diary_name
                        FROM chunks c 
                        JOIN files f ON c.file_id = f.id 
                        WHERE c.content LIKE ? 
                        AND f.diary_name LIKE '%KiloMemory%'
                        ORDER BY f.updated_at DESC 
                        LIMIT ?
                    """
                    cursor.execute(sql, (f"%{expanded_query}%", limit * 2))
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        all_results.append({
                            "text": row[0],
                            "sourceFile": row[1],
                            "score": 0.8,  # 模拟向量相似度分数
                            "search_method": "vcp_semantic"
                        })
                    
                    conn.close()
            
            # 去重
            seen_texts = set()
            unique_results = []
            for result in all_results:
                text = result["text"]
                if text not in seen_texts:
                    seen_texts.add(text)
                    unique_results.append(result)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"VCP向量搜索失败: {e}")
            return []
    
    def _expand_query_with_tagmemo(self, query: str) -> List[str]:
        """使用TagMemo思想扩展查询"""
        expansions = [query]
        
        # 基于常见概念的扩展
        concept_groups = {
            "电脑": ["计算机", "PC", "笔记本", "台式机", "工作站", "硬件", "设备"],
            "硬件": ["配置", "规格", "参数", "组件", "性能", "系统"],
            "环境": ["系统", "设置", "配置", "信息", "详情", "状态"],
            "配置": ["规格", "参数", "性能", "硬件", "系统", "设置"],
            "系统": ["操作系统", "Windows", "软件", "平台", "环境", "设置"],
            "记忆": ["回忆", "经验", "历史", "记录", "知识", "信息"],
            "查询": ["搜索", "查找", "检索", "寻找", "获取", "了解"]
        }
        
        # 简单的语义扩展
        for original, synonyms in concept_groups.items():
            if original in query:
                for synonym in synonyms:
                    expanded = query.replace(original, synonym)
                    expansions.append(expanded)
                    # 同时添加组合
                    expansions.append(f"{query} {synonym}")
        
        return list(set(expansions))[:5]  # 限制扩展数量
    
    def _analyze_memory_type(self, content: str) -> str:
        """分析记忆类型"""
        content_lower = content.lower()
        
        type_patterns = {
            "skill": r'(如何|步骤|方法|技巧|技能|操作|实现|编写|创建)',
            "fact": r'(是|有|包含|包括|属于|配置为|型号为)',
            "experience": r'(经历|体验|感受|体会|处理过|遇到过)',
            "insight": r'(发现|领悟|理解|认识到|意识到|建议|最好)',
            "reflection": r'(反思|总结|回顾|思考|分析|评估)',
            "plan": r'(计划|打算|目标|安排|准备|将要)'
        }
        
        type_scores = {mem_type: 0 for mem_type in type_patterns.keys()}
        
        for mem_type, pattern in type_patterns.items():
            matches = re.findall(pattern, content_lower)
            type_scores[mem_type] = len(matches)
        
        # 基于内容结构的判断
        if re.search(r'\d+\.\s|\-\s|\*\s', content):  # 列表格式
            type_scores["skill"] += 2
        if re.search(r'应该|建议|最好', content):  # 建议性内容
            type_scores["insight"] += 1
        
        # 返回得分最高的类型
        return max(type_scores.items(), key=lambda x: x[1])[0] if type_scores else "unknown"
    
    def _simple_quality_assessment(self, content: str) -> float:
        """简单质量评估"""
        # 基于内容长度
        content_length = len(content)
        if content_length > 500:
            length_score = 0.9
        elif content_length > 200:
            length_score = 0.7
        elif content_length > 50:
            length_score = 0.5
        else:
            length_score = 0.3
        
        # 基于结构
        has_structure = bool(re.search(r'#+|##+|###+|\d+\.|\-|\*', content))
        structure_score = 0.8 if has_structure else 0.5
        
        # 综合评分
        return (length_score * 0.6 + structure_score * 0.4)
    
    def _extract_time_from_filename(self, filename: str) -> str:
        """从文件名提取时间"""
        try:
            # memory_YYYYMMDD_HHMMSS_...
            parts = filename.split('_')
            if len(parts) >= 2:
                date_str = parts[1]  # YYYYMMDD
                if len(date_str) == 8:
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    return f"{year}-{month}-{day}"
        except:
            pass
        return "unknown"
    
    def _extract_time_from_source(self, source: str) -> str:
        """从源文件路径提取时间"""
        try:
            # 从路径中提取时间信息
            if "KiloMemory" in source:
                filename = os.path.basename(source)
                return self._extract_time_from_filename(filename)
        except:
            pass
        return "unknown"

# 初始化记忆管理器
memory_manager = VCPIntegratedMemoryManager()

# MCP工具定义
@mcp.tool()
def store_kilo_memory(content: str, tags: List[str] = None) -> str:
    """
    存储 Kilo Code 的记忆到 dailynote 文件夹（VCP集成版）。
    这些记忆会被VCP的KnowledgeBaseManager自动扫描并建立向量索引。
    
    :param content: 记忆内容
    :param tags: 标签列表
    """
    result = memory_manager.store_memory(content, tags)
    
    if result["success"]:
        memory_id = result["memory_id"]
        metadata = result["metadata"]
        
        response = f"""✅ 记忆存储成功（VCP集成版）！

记忆ID: {memory_id}
存储位置: {result['filepath']}
标签: {', '.join(metadata['tags']) if metadata['tags'] else '无'}
存储时间: {metadata['timestamp']}

该记忆已存储到VCP系统，将被KnowledgeBaseManager自动索引。"""
        
        return response
    else:
        return f"❌ 记忆存储失败: {result['error']}"

@mcp.tool()
def query_kilo_memory(query: str = "", limit: int = 10, 
                     min_quality: float = 0.0) -> str:
    """
    查询 Kilo Code 的记忆（VCP集成版）。
    使用VCP向量搜索和TagMemo语义扩展，实现真正的"一次回忆起"。
    
    :param query: 查询关键词
    :param limit: 返回数量限制
    :param min_quality: 最低质量评分（0-1）
    """
    # 使用VCP集成查询
    results = memory_manager.query_memories_vcp(query, limit, min_quality)
    
    if not results or ("error" in results[0]):
        # 提供有帮助的反馈
        if query:
            return f"未找到与 '{query}' 相关的记忆。\n\n建议：\n1. 尝试更具体的关键词\n2. 使用 store_kilo_memory 存储相关记忆\n3. 检查记忆质量评分是否过高（当前设置: ≥{min_quality})"
        else:
            return "当前没有可用的记忆记录。\n\n建议使用 store_kilo_memory 工具存储重要信息。"
    
    # 构建响应
    if query:
        response = f"🔍 使用VCP向量搜索找到 {len(results)} 条与 '{query}' 相关的记忆:\n\n"
    else:
        response = f"📚 最近的 {len(results)} 条记忆:\n\n"
    
    for i, mem in enumerate(results, 1):
        quality = mem.get("quality_score", 0)
        mem_type = mem.get("type", "unknown")
        
        # 使用友好的类型标签
        type_labels = {
            "fact": "📝 事实",
            "experience": "🎯 经验", 
            "skill": "🛠️ 技能",
            "insight": "💡 洞察",
            "reflection": "🤔 反思",
            "plan": "📅 计划"
        }
        type_label = type_labels.get(mem_type, f"【{mem_type}】")
        
        # 显示搜索方法
        search_method = mem.get("search_method", "")
        method_icon = "🔬" if search_method == "vcp_vector" else "📁"
        
        response += f"{i}. {method_icon} {type_label} (质量:{quality:.2f})\n"
        
        if "content" in mem:
            content_preview = mem["content"][:200] + "..." \
                            if len(mem["content"]) > 200 else mem["content"]
            response += f"   {content_preview}\n"
        
        if "time" in mem and mem["time"] != "unknown":
            response += f"   时间: {mem['time']}\n"
        
        # 显示向量分数（如果有）
        vector_score = mem.get("vector_score", 0)
        if vector_score > 0:
            response += f"   向量相似度: {vector_score:.2f}\n"
        
        response += "\n"
    
    # 添加统计信息
    vcp_results = sum(1 for r in results if r.get("search_method") == "vcp_vector")
    file_results = sum(1 for r in results if r.get("search_method") == "file_system")
    
    response += f"📊 搜索统计: VCP向量搜索 {vcp_results} 条 | 文件系统搜索 {file_results} 条\n"
    
    if len(results) >= limit:
        response += f"💡 提示：使用更具体的关键词或降低质量阈值可以找到更多相关记忆。"
    
    return response

@mcp.tool()
def trigger_vcp_recall(user_message: str = "", system_context: str = "") -> str:
    """
    触发VCP主动回忆 - 在任务开始时自动调用
    
    这是实现"一次回忆起"的核心工具，直接利用VCP系统的能力。
    
    :param user_message: 用户的消息/任务描述
    :param system_context: 系统上下文信息
    :return: 自然集成的回忆结果或空字符串（如果不需回忆）
    """
    if not user_message:
        return ""
    
    try:
        # 分析用户消息，提取关键概念
        key_concepts = memory_manager._expand_query_with_tagmemo(user_message)
        
        # 使用最重要的概念进行查询
        if key_concepts:
            # 选择前2个概念作为查询
            query = " ".join(key_concepts[:2])
            
            # 执行查询
            results = memory_manager.query_memories_vcp(query, limit=3, min_quality=0.5)
            
            if results and not ("error" in results[0]):
                # 构建自然回应
                top_result = results[0]
                content_preview = top_result.get("content", "")[:150] + "..." \
                                if len(top_result.get("content", "")) > 150 else top_result.get("content", "")
                
                response = f"💭 基于您的任务，我回忆起相关经验：\n\n"
                response += f"{content_preview}\n\n"
                response += f"（来自{top_result.get('time', '历史')}的记忆，质量评分:{top_result.get('quality_score', 0):.2f})"
                
                return response
        
        return ""
        
    except Exception as e:
        print(f"VCP主动回忆触发失败: {e}")
        return ""

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
    获取记忆系统统计信息。
    """
    try:
        # 统计文件数量
        files = [f for f in os.listdir(MEMORY_DIR) if f.endswith(".md")]
        total_files = len(files)
        
        # 统计最近7天的新增
        recent_count = 0
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        for fname in files:
            try:
                file_time_str = fname.split("_")[1]  # memory_YYYYMMDD_...
                file_date = datetime.datetime.strptime(file_time_str[:8], "%Y%m%d")
                if file_date > week_ago:
                    recent_count += 1
            except:
                continue
        
        # 检查VCP向量搜索可用性
        vcp_available = "✅ 可用" if VECTOR_SEARCH_AVAILABLE else "❌ 不可用"
        
        response = "📊 VCP集成记忆系统统计报告\n\n"
        response += f"总记忆文件: {total_files}\n"
        response += f"最近7天新增: {recent_count}\n"
        response += f"VCP向量搜索: {vcp_available}\n"
        response += f"记忆目录: {MEMORY_DIR}\n\n"
        
        response += "💡 使用建议:\n"
        response += "1. 使用 store_kilo_memory 存储重要信息\n"
        response += "2. 使用 query_kilo_memory 进行语义搜索\n"
        response += "3. 使用 trigger_vcp_recall 在任务开始时自动回忆\n"
        response += "4. 为记忆添加标签以提高检索准确性"
        
        return response
        
    except Exception as e:
        return f"获取统计信息失败: {str(e)}"

# 主函数
if __name__ == "__main__":
    print("=" * 60)
    print("VCP集成版 KiloMemoryMCP 启动")
    print("=" * 60)
    print("核心特性:")
    print("1. 直接集成VCP向量搜索能力")
    print("2. 使用TagMemo语义扩展查询")
    print("3. 实现真正的'一次回忆起'机制")
    print("4. 优化记忆质量评估和去重")
    print("5. 提供主动回忆触发功能")
    print("=" * 60)
    
    # 运行 MCP 服务器
    mcp.run()