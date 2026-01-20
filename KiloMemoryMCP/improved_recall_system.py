"""
改进的回忆触发系统 - 实现"一次回忆起"、"主动回忆起"、"自然而然不自觉回忆起"

核心设计原则：
1. 上下文感知：自动分析当前对话上下文，提取关键概念
2. 主动触发：在任务开始时自动检索相关记忆
3. 质量优先：根据记忆质量评分自动筛选
4. 自然融合：将回忆结果自然融入对话，不打断流程
"""

import os
import re
import json
import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum

class RecallTrigger(Enum):
    """回忆触发类型"""
    TASK_START = "task_start"      # 任务开始时
    CONTEXT_CHANGE = "context_change" # 上下文变化时
    KEYWORD_MATCH = "keyword_match"   # 关键词匹配时
    TIME_BASED = "time_based"        # 时间触发（如每日回顾）
    PROACTIVE = "proactive"          # 主动触发（基于预测）

class ContextAnalyzer:
    """上下文分析器"""
    
    def __init__(self):
        self.current_context = ""
        self.context_history = []
        self.key_concepts = set()
        
    def analyze_context(self, user_message: str, system_context: str = "") -> Dict:
        """分析当前上下文，提取关键信息"""
        combined_context = f"{system_context}\n{user_message}"
        self.current_context = combined_context
        
        # 提取关键概念
        concepts = self._extract_concepts(combined_context)
        self.key_concepts.update(concepts)
        
        # 分析任务类型
        task_type = self._identify_task_type(combined_context)
        
        # 分析信息需求
        info_needs = self._identify_info_needs(combined_context)
        
        return {
            "concepts": list(concepts),
            "task_type": task_type,
            "info_needs": info_needs,
            "context_hash": hash(combined_context) % 10000
        }
    
    def _extract_concepts(self, text: str) -> List[str]:
        """提取关键概念"""
        concepts = []
        
        # 提取技术术语（大写字母开头、驼峰命名）
        concepts.extend(re.findall(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', text))
        
        # 提取中文关键词（3-6字的名词短语）
        concepts.extend(re.findall(r'[\u4e00-\u9fa5]{3,6}', text))
        
        # 提取引号内容
        concepts.extend(re.findall(r'["\'](.*?)["\']', text))
        
        # 提取括号内容
        concepts.extend(re.findall(r'[【(（](.*?)[】)）]', text))
        
        # 去重和清理
        concepts = [c.strip() for c in concepts if len(c.strip()) > 1]
        return list(set(concepts))
    
    def _identify_task_type(self, text: str) -> str:
        """识别任务类型 - 通用版本"""
        text_lower = text.lower()
        
        # 更通用的任务类型识别
        task_patterns = {
            "technical": ["代码", "编程", "实现", "函数", "类", "方法", "bug", "错误", "调试", "修复", "问题", "异常", "崩溃"],
            "planning": ["计划", "设计", "架构", "方案", "策略", "规划", "安排"],
            "learning": ["学习", "了解", "研究", "探索", "教程", "知识", "概念"],
            "memory": ["回忆", "记忆", "想起", "之前", "历史", "经验", "过去"],
            "system": ["系统", "配置", "环境", "硬件", "软件", "电脑", "设备", "网络"],
            "creative": ["创作", "写作", "绘画", "设计", "艺术", "创意", "灵感"],
            "analysis": ["分析", "评估", "比较", "统计", "数据", "报告", "总结"],
            "communication": ["沟通", "交流", "对话", "讨论", "会议", "邮件", "消息"]
        }
        
        # 计算匹配分数，选择最高分的任务类型
        scores = {}
        for task_type, keywords in task_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                scores[task_type] = matches / len(keywords)
        
        if scores:
            # 返回最高分的任务类型
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    def _identify_info_needs(self, text: str) -> List[str]:
        """识别信息需求"""
        needs = []
        text_lower = text.lower()
        
        need_patterns = {
            "how_to": ["如何", "怎么", "步骤", "方法"],
            "what_is": ["是什么", "什么是", "定义", "概念"],
            "why": ["为什么", "原因", "为何"],
            "example": ["例子", "示例", "样例", "示范"],
            "reference": ["参考", "文档", "资料", "链接"],
            "history": ["之前", "历史", "上次", "以前"]
        }
        
        for need_type, keywords in need_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                needs.append(need_type)
        
        return needs

class ProactiveRecallEngine:
    """主动回忆引擎"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.context_analyzer = ContextAnalyzer()
        self.recall_threshold = 0.6  # 回忆触发阈值
        self.last_recall_time = None
        
    def should_recall(self, user_message: str, system_context: str = "") -> Tuple[bool, Dict]:
        """判断是否应该触发回忆"""
        # 分析当前上下文
        context_analysis = self.context_analyzer.analyze_context(user_message, system_context)
        
        # 检查触发条件
        triggers = self._check_triggers(context_analysis)
        
        if triggers:
            return True, {
                "triggers": triggers,
                "context": context_analysis,
                "reason": "检测到多个回忆触发条件"
            }
        
        return False, {}
    
    def _check_triggers(self, context_analysis: Dict) -> List[str]:
        """检查各种触发条件"""
        triggers = []
        
        # 1. 任务类型触发
        if context_analysis["task_type"] in ["memory", "system", "debugging"]:
            triggers.append(RecallTrigger.TASK_START.value)
        
        # 2. 关键词触发
        if context_analysis["concepts"]:
            triggers.append(RecallTrigger.KEYWORD_MATCH.value)
        
        # 3. 信息需求触发
        if context_analysis["info_needs"]:
            triggers.append(RecallTrigger.PROACTIVE.value)
        
        # 4. 时间触发（如果距离上次回忆超过30分钟）
        if self._should_time_trigger():
            triggers.append(RecallTrigger.TIME_BASED.value)
        
        return triggers
    
    def _should_time_trigger(self) -> bool:
        """时间触发检查"""
        if not self.last_recall_time:
            return True
        
        time_diff = datetime.datetime.now() - self.last_recall_time
        return time_diff.total_seconds() > 1800  # 30分钟
    
    def execute_recall(self, context_analysis: Dict) -> Dict:
        """执行回忆操作"""
        try:
            # 构建查询
            query = self._build_query(context_analysis)
            
            # 执行查询
            results = self.memory_manager.query_memories(
                query=query,
                limit=5,
                min_quality=0.5
            )
            
            # 更新最后回忆时间
            self.last_recall_time = datetime.datetime.now()
            
            # 分析结果
            analyzed_results = self._analyze_results(results, context_analysis)
            
            return {
                "success": True,
                "query": query,
                "results": analyzed_results,
                "context": context_analysis
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_query(self, context_analysis: Dict) -> str:
        """构建通用查询语句"""
        concepts = context_analysis["concepts"]
        task_type = context_analysis["task_type"]
        info_needs = context_analysis["info_needs"]
        
        # 通用查询构建策略
        query_parts = []
        
        # 1. 添加关键概念（最多3个）
        if concepts:
            # 优先选择名词性概念
            noun_concepts = [c for c in concepts if len(c) >= 2]
            query_parts.extend(noun_concepts[:3])
        
        # 2. 基于任务类型添加通用关键词
        generic_keywords = {
            "technical": ["技术", "实现", "代码"],
            "planning": ["计划", "设计", "方案"],
            "learning": ["学习", "知识", "理解"],
            "memory": ["回忆", "经验", "历史"],
            "system": ["系统", "配置", "环境"],
            "creative": ["创作", "灵感", "设计"],
            "analysis": ["分析", "数据", "评估"],
            "communication": ["沟通", "交流", "对话"]
        }
        
        if task_type in generic_keywords:
            query_parts.extend(generic_keywords[task_type][:2])
        
        # 3. 基于信息需求添加关键词
        need_keywords = {
            "how_to": "如何",
            "what_is": "是什么",
            "why": "为什么",
            "example": "例子",
            "reference": "参考",
            "history": "历史"
        }
        
        for need in info_needs:
            if need in need_keywords:
                query_parts.append(need_keywords[need])
        
        # 4. 如果没有足够的概念，添加通用查询词
        if len(query_parts) < 2:
            query_parts.extend(["经验", "知识", "信息"])
        
        # 构建最终查询
        query = " ".join(query_parts) if query_parts else ""
        return query
    
    def _analyze_results(self, results: List[Dict], context_analysis: Dict) -> List[Dict]:
        """分析回忆结果"""
        analyzed = []
        
        for result in results:
            if "error" in result:
                continue
            
            # 计算相关性分数
            relevance_score = self._calculate_relevance(result, context_analysis)
            
            analyzed.append({
                "content": result.get("content", ""),
                "quality_score": result.get("quality_score", 0),
                "relevance_score": relevance_score,
                "type": result.get("type", "unknown"),
                "source": result.get("source", ""),
                "time": result.get("time", "")
            })
        
        # 按相关性排序
        analyzed.sort(key=lambda x: x["relevance_score"], reverse=True)
        return analyzed
    
    def _calculate_relevance(self, result: Dict, context_analysis: Dict) -> float:
        """计算通用相关性分数"""
        content = result.get("content", "").lower()
        concepts = context_analysis["concepts"]
        task_type = context_analysis["task_type"]
        
        # 1. 概念匹配度（40%权重）
        concept_score = 0
        if concepts:
            concept_matches = sum(1 for concept in concepts if concept.lower() in content)
            concept_score = concept_matches / len(concepts)
        
        # 2. 任务类型匹配度（30%权重）
        task_score = 0
        task_keyword_groups = {
            "technical": ["代码", "函数", "类", "方法", "调试", "修复", "问题", "异常"],
            "planning": ["计划", "设计", "架构", "方案", "策略", "规划"],
            "learning": ["学习", "知识", "理解", "研究", "探索", "教程"],
            "memory": ["回忆", "经验", "历史", "过去", "之前", "记忆"],
            "system": ["系统", "配置", "环境", "硬件", "软件", "电脑"],
            "creative": ["创作", "灵感", "设计", "艺术", "创意", "写作"],
            "analysis": ["分析", "数据", "评估", "统计", "报告", "总结"],
            "communication": ["沟通", "交流", "对话", "讨论", "会议", "消息"]
        }
        
        if task_type in task_keyword_groups:
            keywords = task_keyword_groups[task_type]
            keyword_matches = sum(1 for kw in keywords if kw in content)
            task_score = keyword_matches / len(keywords) if keywords else 0
        
        # 3. 内容质量分数（20%权重）
        quality_score = result.get("quality_score", 0)
        
        # 4. 时间衰减因子（10%权重）
        time_score = self._calculate_time_score(result.get("time", ""))
        
        # 综合评分
        relevance = (
            concept_score * 0.4 +
            task_score * 0.3 +
            quality_score * 0.2 +
            time_score * 0.1
        )
        
        return min(relevance, 1.0)
    
    def _calculate_time_score(self, time_str: str) -> float:
        """计算时间衰减分数（越新分数越高）"""
        if not time_str:
            return 0.5
        
        try:
            # 尝试解析时间字符串
            from datetime import datetime
            memory_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            current_time = datetime.now()
            
            # 计算时间差（天数）
            time_diff = (current_time - memory_time).days
            
            # 时间衰减函数：30天内为1.0，之后指数衰减
            if time_diff <= 30:
                return 1.0
            else:
                # 指数衰减：e^(-0.05*(days-30))
                import math
                return math.exp(-0.05 * (time_diff - 30))
                
        except Exception:
            return 0.5

class NaturalRecallIntegrator:
    """自然回忆集成器 - 将回忆结果自然融入对话"""
    
    def __init__(self):
        self.integration_styles = {
            "casual": "我想起之前处理过类似的情况：",
            "professional": "根据历史记录，相关解决方案包括：",
            "reflective": "这让我回想起之前的经验：",
            "helpful": "我之前学到的一些相关内容："
        }
    
    def integrate_recall(self, recall_results: Dict, style: str = "helpful") -> str:
        """将回忆结果自然集成到对话中"""
        if not recall_results.get("success") or not recall_results.get("results"):
            return ""
        
        results = recall_results["results"]
        context = recall_results.get("context", {})
        
        # 选择集成风格
        integration_style = self.integration_styles.get(style, self.integration_styles["helpful"])
        
        # 构建自然回应
        response_parts = [f"{integration_style}\n\n"]
        
        # 添加最相关的1-2个结果
        for i, result in enumerate(results[:2]):
            if result["relevance_score"] > 0.7:  # 高相关性
                content_preview = self._summarize_content(result["content"])
                response_parts.append(f"• {content_preview}\n")
        
        # 如果有更多相关结果，简要提及
        if len(results) > 2:
            additional_count = len(results) - 2
            response_parts.append(f"\n还有{additional_count}条相关记忆可供参考。")
        
        return "\n".join(response_parts)
    
    def _summarize_content(self, content: str, max_length: int = 150) -> str:
        """摘要化内容"""
        if len(content) <= max_length:
            return content
        
        # 尝试找到句子边界
        sentences = re.split(r'[。！？.!?]', content)
        summary = ""
        
        for sentence in sentences:
            if len(summary) + len(sentence) <= max_length:
                summary += sentence + "。"
            else:
                break
        
        if not summary:
            # 如果找不到完整句子，直接截断
            summary = content[:max_length-3] + "..."
        
        return summary

# 主入口函数
def setup_enhanced_recall_system(memory_manager):
    """设置增强回忆系统"""
    recall_engine = ProactiveRecallEngine(memory_manager)
    integrator = NaturalRecallIntegrator()
    
    return {
        "recall_engine": recall_engine,
        "integrator": integrator,
        "context_analyzer": recall_engine.context_analyzer
    }

# 使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("增强回忆系统演示")
    print("=" * 60)
    
    # 模拟内存管理器
    class MockMemoryManager:
        def query_memories(self, query, limit, min_quality):
            return [
                {
                    "content": "之前处理过Windows 11系统配置问题，需要检查显卡驱动和电源管理设置。",
                    "quality_score": 0.8,
                    "type": "experience",
                    "source": "memory_20260120_abc123.md",
                    "time": "2026-01-20T10:30:00"
                },
                {
                    "content": "ROG Strix笔记本的硬件配置包括i9处理器和RTX 4090显卡。",
                    "quality_score": 0.9,
                    "type": "fact",
                    "source": "memory_20260120_def456.md",
                    "time": "2026-01-20T11:45:00"
                }
            ]
    
    # 创建系统
    memory_manager = MockMemoryManager()
    recall_system = setup_enhanced_recall_system(memory_manager)
    
    # 测试用例
    test_messages = [
        "我的电脑硬件配置是什么？",
        "如何优化Windows 11的性能？",
        "之前处理过系统配置问题吗？"
    ]
    
    for msg in test_messages:
        print(f"\n用户消息: {msg}")
        
        # 检查是否应该回忆
        should_recall, recall_info = recall_system["recall_engine"].should_recall(msg)
        
        if should_recall:
            print(f"触发回忆: {recall_info['triggers']}")
            
            # 执行回忆
            recall_results = recall_system["recall_engine"].execute_recall(recall_info["context"])
            
            # 自然集成
            natural_response = recall_system["integrator"].integrate_recall(recall_results)
            
            if natural_response:
                print(f"自然回忆回应:\n{natural_response}")
        else:
            print("未触发回忆")
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)