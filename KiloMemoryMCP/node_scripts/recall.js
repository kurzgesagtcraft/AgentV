
const path = require('path');
const fs = require('fs');

// 加载环境变量
const envPath = path.join(__dirname, '..', '..', 'config.env');
if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    envContent.split('\n').forEach(line => {
        const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
        if (match) {
            const key = match[1];
            let value = match[2] || '';
            
            // 移除注释
            if (value.includes('#')) {
                value = value.split('#')[0].trim();
            }
            
            // 移除引号
            value = value.replace(/^['"]|['"]$/g, '').trim();
            
            if (!process.env[key]) {
                process.env[key] = value;
            }
        }
    });
}

const KnowledgeBaseManager = require(path.join(__dirname, '..', '..', 'KnowledgeBaseManager.js'));
const { getSingleEmbedding } = require(path.join(__dirname, '..', '..', 'EmbeddingUtils'));

function extractKeywords(text) {
    const words = text.toLowerCase()
        .replace(/[^\w\u4e00-\u9fa5\s]/g, ' ')
        .split(/\s+/)
        .filter(word => word.length > 1);
    
    return [...new Set(words)].slice(0, 10);
}

function buildRecallQuery(context, keywords) {
    if (keywords.length > 0) {
        return `${context} ${keywords.join(' ')}`;
    }
    return context;
}

function classifyRelevance(score) {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    if (score >= 0.4) return 'low';
    return 'very_low';
}

async function main() {
    try {
        const args = JSON.parse(process.argv[2]);
        const { context, maxMemories = 5 } = args;
        
        // 初始化知识库管理器
        const kbManager = KnowledgeBaseManager;
        await kbManager.initialize();
        
        // 提取关键词
        const keywords = extractKeywords(context);
        
        // 构建搜索查询
        const searchQuery = buildRecallQuery(context, keywords);
        
        // 获取查询向量
        const queryVector = await getSingleEmbedding(searchQuery, {
            apiKey: process.env.API_Key,
            apiUrl: process.env.API_URL,
            model: process.env.WhitelistEmbeddingModel || 'text-embedding-3-small'
        });
        
        if (!queryVector) {
            console.log(JSON.stringify({ 
                success: false, 
                error: "查询向量化失败" 
            }));
            return;
        }
        
        // 搜索知识库（使用较高的tagBoost以增强语义扩展）
        const searchResults = await kbManager.search(queryVector, maxMemories * 2, 0.7);
        
        // 过滤和排序结果
        const relevantResults = searchResults
            .filter(result => result.score >= 0.3)
            .slice(0, maxMemories)
            .map((result, index) => ({
                id: `recall_${Date.now()}_${index}`,
                text: result.text,
                score: result.score,
                source: result.sourceFile,
                relevance: classifyRelevance(result.score),
                matchedTags: result.matchedTags || [],
                timestamp: new Date().toISOString()
            }));
        
        // 构建回忆总结
        let summary;
        if (relevantResults.length === 0) {
            summary = `基于当前上下文"${context.substring(0, 50)}..."，没有找到相关的历史记忆。`;
        } else {
            const memoryCount = relevantResults.length;
            const avgRelevance = relevantResults.reduce((sum, m) => sum + m.score, 0) / memoryCount;
            const relevanceLevel = classifyRelevance(avgRelevance);
            
            const tagSet = new Set();
            relevantResults.forEach(memory => {
                memory.matchedTags.forEach(tag => tagSet.add(tag));
            });
            const topTags = Array.from(tagSet).slice(0, 5);
            
            summary = `基于当前上下文，系统主动回忆了 ${memoryCount} 个相关记忆（平均相关性：${relevanceLevel}）。`;
            if (topTags.length > 0) {
                summary += ` 相关标签：${topTags.join('、')}`;
            }
        }
        
        console.log(JSON.stringify({
            success: true,
            context: context,
            memories: relevantResults,
            summary: summary,
            stats: {
                totalFound: searchResults.length,
                relevantFound: relevantResults.length,
                averageRelevance: relevantResults.length > 0 
                    ? relevantResults.reduce((sum, r) => sum + r.score, 0) / relevantResults.length 
                    : 0
            }
        }));
        
    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message
        }));
    }
}

main();
