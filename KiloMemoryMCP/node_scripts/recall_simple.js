// 简化版主动回忆脚本
const path = require('path');
const fs = require('fs').promises;

async function main() {
    try {
        const args = JSON.parse(process.argv[2]);
        const { context, maxMemories = 5 } = args;
        
        console.log(`[Recall] 开始主动回忆: "${context.substring(0, 50)}..."`);
        
        // 模拟搜索记忆
        const memories = [
            {
                id: "test_1",
                text: "在Python异步编程中遇到死锁问题时，可以使用asyncio.wait_for()设置超时，或者使用asyncio.shield()保护重要任务。",
                score: 0.85,
                source: "memory_20260121_ed2a513549da.md",
                relevance: "high",
                matchedTags: ["Python", "异步编程", "死锁", "asyncio"],
                timestamp: new Date().toISOString()
            },
            {
                id: "test_2",
                text: "在Python异步编程中，需要注意避免阻塞操作，否则会阻塞整个事件循环。使用asyncio.sleep()而不是time.sleep()。",
                score: 0.75,
                source: "memory_20260121_a452c6e2ee09.md",
                relevance: "medium",
                matchedTags: ["Python", "异步编程", "阻塞", "事件循环"],
                timestamp: new Date().toISOString()
            }
        ];
        
        // 构建回忆总结
        let summary;
        if (memories.length === 0) {
            summary = `基于当前上下文"${context.substring(0, 50)}..."，没有找到相关的历史记忆。`;
        } else {
            const memoryCount = memories.length;
            const avgRelevance = memories.reduce((sum, m) => sum + m.score, 0) / memoryCount;
            const relevanceLevel = avgRelevance >= 0.8 ? '高' : avgRelevance >= 0.6 ? '中' : '低';
            
            const tagSet = new Set();
            memories.forEach(memory => {
                memory.matchedTags.forEach(tag => tagSet.add(tag));
            });
            const topTags = Array.from(tagSet).slice(0, 5);
            
            summary = `基于当前上下文，系统主动回忆了 ${memoryCount} 个相关记忆（平均相关性：${relevanceLevel}）。`;
            if (topTags.length > 0) {
                summary += ` 相关标签：${topTags.join('、')}`;
            }
        }
        
        const result = {
            success: true,
            context: context,
            memories: memories.slice(0, maxMemories),
            summary: summary,
            stats: {
                totalFound: memories.length,
                relevantFound: Math.min(memories.length, maxMemories),
                averageRelevance: memories.length > 0 
                    ? memories.reduce((sum, r) => sum + r.score, 0) / memories.length 
                    : 0
            }
        };
        
        console.log(JSON.stringify(result, null, 2));
        
    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message
        }));
    }
}

main();