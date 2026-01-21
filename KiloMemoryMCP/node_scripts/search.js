
const { KnowledgeBaseManager } = require('../KnowledgeBaseManager.js');
const { getSingleEmbedding } = require('../EmbeddingUtils');

async function main() {
    try {
        const args = JSON.parse(process.argv[2]);
        const { query, limit = 10, tagBoost = 0.5 } = args;
        
        // 初始化知识库管理器
        const kbManager = KnowledgeBaseManager;
        await kbManager.initialize();
        
        // 获取查询向量
        const queryVector = await getSingleEmbedding(query, {
            apiKey: process.env.API_Key,
            apiUrl: process.env.API_URL,
            model: process.env.WhitelistEmbeddingModel || 'text-embedding-3-small'
        });
        
        if (!queryVector) {
            console.log(JSON.stringify({ success: false, error: "查询向量化失败" }));
            return;
        }
        
        // 执行搜索
        const results = await kbManager.search(queryVector, limit, tagBoost);
        
        console.log(JSON.stringify({
            success: true,
            results: results.map(r => ({
                text: r.text,
                sourceFile: r.sourceFile,
                score: r.score,
                matchedTags: r.matchedTags || [],
                boostFactor: r.boostFactor || 0
            }))
        }));
        
    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message
        }));
    }
}

main();
