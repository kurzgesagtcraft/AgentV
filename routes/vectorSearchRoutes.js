// routes/vectorSearchRoutes.js
// VCPToolBox 向量搜索API端点 - 为KiloMemoryMCP提供真正的VCP API集成

const express = require('express');
const path = require('path');

module.exports = function(knowledgeBaseManager, DEBUG_MODE) {
    const vectorSearchRouter = express.Router();

    /**
     * 向量搜索API端点
     * POST /api/search
     * 请求体: {
     *   query: "搜索查询文本",
     *   limit: 10, // 可选，返回结果数量
     *   diaryName: "日记本名称", // 可选，指定搜索特定日记本
     *   tagBoost: 0.5, // 可选，TagMemo增强因子 (0-1)
     *   minScore: 0.0, // 可选，最小相似度分数
     *   includeTags: true // 可选，是否包含匹配的标签信息
     * }
     */
    vectorSearchRouter.post('/search', async (req, res) => {
        try {
            const { query, limit = 10, diaryName = null, tagBoost = 0.5, minScore = 0.0, includeTags = true } = req.body;

            if (!query || typeof query !== 'string' || query.trim() === '') {
                return res.status(400).json({
                    success: false,
                    error: '查询文本不能为空'
                });
            }

            if (DEBUG_MODE) {
                console.log(`[VectorSearchAPI] 收到搜索请求: "${query.substring(0, 50)}..."`);
                console.log(`[VectorSearchAPI] 参数: limit=${limit}, diaryName=${diaryName}, tagBoost=${tagBoost}`);
            }

            // 1. 获取查询文本的向量嵌入
            const getSingleEmbedding = require('../EmbeddingUtils').getSingleEmbedding;
            const queryVector = await getSingleEmbedding(query, {
                apiKey: process.env.API_Key,
                apiUrl: process.env.API_URL,
                model: process.env.WhitelistEmbeddingModel || 'google/gemini-embedding-001'
            });

            if (!queryVector || !Array.isArray(queryVector)) {
                return res.status(500).json({
                    success: false,
                    error: '查询向量化失败'
                });
            }

            // 2. 应用TagMemo增强（如果启用）
            let enhancedVector = queryVector;
            let tagBoostInfo = null;
            
            if (tagBoost > 0 && knowledgeBaseManager && typeof knowledgeBaseManager.applyTagBoost === 'function') {
                if (DEBUG_MODE) console.log(`[VectorSearchAPI] 应用TagMemo增强，因子: ${tagBoost}`);
                
                const boostResult = knowledgeBaseManager.applyTagBoost(new Float32Array(queryVector), tagBoost);
                if (boostResult && boostResult.vector) {
                    enhancedVector = Array.from(boostResult.vector);
                    tagBoostInfo = boostResult.info;
                    
                    if (DEBUG_MODE && tagBoostInfo) {
                        console.log(`[VectorSearchAPI] TagMemo匹配标签: ${tagBoostInfo.matchedTags?.slice(0, 5).join(', ')}`);
                    }
                }
            }

            // 3. 执行向量搜索
            let searchResults = [];
            if (diaryName) {
                // 搜索特定日记本
                searchResults = await knowledgeBaseManager.search(diaryName, enhancedVector, limit, tagBoost);
            } else {
                // 搜索所有日记本
                searchResults = await knowledgeBaseManager.search(enhancedVector, limit, tagBoost);
            }

            // 4. 过滤结果（按最小分数）
            const filteredResults = searchResults.filter(result => result.score >= minScore);

            // 5. 格式化响应
            const formattedResults = filteredResults.map((result, index) => ({
                id: index + 1,
                text: result.text,
                score: result.score,
                sourceFile: result.sourceFile,
                fullPath: result.fullPath,
                matchedTags: includeTags && result.matchedTags ? result.matchedTags : [],
                boostFactor: result.boostFactor || 0,
                tagMatchScore: result.tagMatchScore || 0,
                tagMatchCount: result.tagMatchCount || 0
            }));

            // 6. 返回响应
            const response = {
                success: true,
                query: query,
                parameters: {
                    limit,
                    diaryName,
                    tagBoost,
                    minScore,
                    includeTags
                },
                tagBoostInfo: includeTags ? tagBoostInfo : null,
                results: formattedResults,
                stats: {
                    totalFound: searchResults.length,
                    totalReturned: formattedResults.length,
                    averageScore: formattedResults.length > 0 
                        ? formattedResults.reduce((sum, r) => sum + r.score, 0) / formattedResults.length 
                        : 0
                }
            };

            if (DEBUG_MODE) {
                console.log(`[VectorSearchAPI] 搜索完成，找到 ${formattedResults.length} 个结果`);
            }

            res.json(response);

        } catch (error) {
            console.error('[VectorSearchAPI] 搜索过程中发生错误:', error);
            res.status(500).json({
                success: false,
                error: '内部服务器错误',
                details: error.message,
                stack: DEBUG_MODE ? error.stack : undefined
            });
        }
    });

    /**
     * 语义标签搜索API端点
     * POST /api/search/tags
     * 请求体: {
     *   query: "标签搜索查询",
     *   limit: 10 // 可选，返回结果数量
     * }
     */
    vectorSearchRouter.post('/search/tags', async (req, res) => {
        try {
            const { query, limit = 10 } = req.body;

            if (!query || typeof query !== 'string' || query.trim() === '') {
                return res.status(400).json({
                    success: false,
                    error: '查询文本不能为空'
                });
            }

            if (DEBUG_MODE) {
                console.log(`[VectorSearchAPI] 收到标签搜索请求: "${query}"`);
            }

            // 搜索相似标签
            const similarTags = await knowledgeBaseManager.searchSimilarTags(query, limit);

            const response = {
                success: true,
                query: query,
                results: similarTags.map((tag, index) => ({
                    id: index + 1,
                    tag: tag.tag,
                    score: tag.score,
                    relevance: (tag.score * 100).toFixed(1) + '%'
                })),
                stats: {
                    totalFound: similarTags.length
                }
            };

            res.json(response);

        } catch (error) {
            console.error('[VectorSearchAPI] 标签搜索过程中发生错误:', error);
            res.status(500).json({
                success: false,
                error: '内部服务器错误',
                details: error.message
            });
        }
    });

    /**
     * 获取日记本列表API端点
     * GET /api/diaries
     */
    vectorSearchRouter.get('/diaries', async (req, res) => {
        try {
            const db = knowledgeBaseManager.db;
            if (!db) {
                return res.status(503).json({
                    success: false,
                    error: '知识库管理器未初始化'
                });
            }

            const stmt = db.prepare('SELECT DISTINCT diary_name, COUNT(*) as file_count FROM files GROUP BY diary_name ORDER BY diary_name');
            const diaries = stmt.all();

            const response = {
                success: true,
                diaries: diaries.map(diary => ({
                    name: diary.diary_name,
                    fileCount: diary.file_count,
                    hasVectorCache: knowledgeBaseManager.diaryNameVectorCache.has(diary.diary_name)
                })),
                stats: {
                    totalDiaries: diaries.length,
                    totalFiles: diaries.reduce((sum, d) => sum + d.file_count, 0)
                }
            };

            res.json(response);

        } catch (error) {
            console.error('[VectorSearchAPI] 获取日记本列表过程中发生错误:', error);
            res.status(500).json({
                success: false,
                error: '内部服务器错误',
                details: error.message
            });
        }
    });

    /**
     * 健康检查API端点
     * GET /api/health
     */
    vectorSearchRouter.get('/health', (req, res) => {
        try {
            const isInitialized = knowledgeBaseManager.initialized;
            const hasTagIndex = knowledgeBaseManager.tagIndex !== null;
            const diaryIndicesCount = knowledgeBaseManager.diaryIndices.size;
            const vectorCacheSize = knowledgeBaseManager.diaryNameVectorCache.size;

            const healthStatus = {
                success: true,
                status: isInitialized ? 'healthy' : 'initializing',
                components: {
                    knowledgeBaseManager: isInitialized ? 'ready' : 'not_ready',
                    tagIndex: hasTagIndex ? 'ready' : 'not_ready',
                    diaryIndices: `${diaryIndicesCount} loaded`,
                    vectorCache: `${vectorCacheSize} entries`
                },
                config: {
                    dimension: knowledgeBaseManager.config.dimension,
                    model: knowledgeBaseManager.config.model,
                    rootPath: knowledgeBaseManager.config.rootPath
                },
                timestamp: new Date().toISOString()
            };

            res.json(healthStatus);

        } catch (error) {
            console.error('[VectorSearchAPI] 健康检查过程中发生错误:', error);
            res.status(500).json({
                success: false,
                error: '内部服务器错误',
                details: error.message
            });
        }
    });

    /**
     * 主动回忆触发API端点
     * POST /api/recall/trigger
     * 请求体: {
     *   context: "当前对话或任务上下文",
     *   maxMemories: 5, // 可选，最大回忆数量
     *   relevanceThreshold: 0.3 // 可选，相关性阈值
     * }
     */
    vectorSearchRouter.post('/recall/trigger', async (req, res) => {
        try {
            const { context, maxMemories = 5, relevanceThreshold = 0.3 } = req.body;

            if (!context || typeof context !== 'string' || context.trim() === '') {
                return res.status(400).json({
                    success: false,
                    error: '上下文文本不能为空'
                });
            }

            if (DEBUG_MODE) {
                console.log(`[VectorSearchAPI] 收到主动回忆触发请求: "${context.substring(0, 100)}..."`);
            }

            // 1. 提取关键词用于搜索
            const keywords = extractKeywords(context);
            
            // 2. 构建搜索查询
            const searchQuery = buildRecallQuery(context, keywords);
            
            // 3. 执行向量搜索
            const getSingleEmbedding = require('../EmbeddingUtils').getSingleEmbedding;
            const queryVector = await getSingleEmbedding(searchQuery, {
                apiKey: process.env.API_Key,
                apiUrl: process.env.API_URL,
                model: process.env.WhitelistEmbeddingModel || 'google/gemini-embedding-001'
            });

            if (!queryVector) {
                return res.status(500).json({
                    success: false,
                    error: '查询向量化失败'
                });
            }

            // 4. 搜索所有日记本（使用较高的tagBoost以增强语义扩展）
            const searchResults = await knowledgeBaseManager.search(queryVector, maxMemories * 2, 0.7);

            // 5. 过滤和排序结果
            const relevantResults = searchResults
                .filter(result => result.score >= relevanceThreshold)
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

            // 6. 构建回忆总结
            const recallSummary = buildRecallSummary(context, relevantResults);

            const response = {
                success: true,
                context: context,
                trigger: {
                    keywords: keywords,
                    searchQuery: searchQuery,
                    parameters: {
                        maxMemories,
                        relevanceThreshold
                    }
                },
                memories: relevantResults,
                summary: recallSummary,
                stats: {
                    totalFound: searchResults.length,
                    relevantFound: relevantResults.length,
                    averageRelevance: relevantResults.length > 0 
                        ? relevantResults.reduce((sum, r) => sum + r.score, 0) / relevantResults.length 
                        : 0
                }
            };

            if (DEBUG_MODE) {
                console.log(`[VectorSearchAPI] 主动回忆完成，找到 ${relevantResults.length} 个相关记忆`);
            }

            res.json(response);

        } catch (error) {
            console.error('[VectorSearchAPI] 主动回忆过程中发生错误:', error);
            res.status(500).json({
                success: false,
                error: '内部服务器错误',
                details: error.message
            });
        }
    });

    // 辅助函数：提取关键词
    function extractKeywords(text) {
        // 简单的关键词提取逻辑
        // 在实际应用中可以使用更复杂的分词算法
        const words = text.toLowerCase()
            .replace(/[^\w\u4e00-\u9fa5\s]/g, ' ')
            .split(/\s+/)
            .filter(word => word.length > 1);
        
        // 去重并返回前10个关键词
        return [...new Set(words)].slice(0, 10);
    }

    // 辅助函数：构建回忆查询
    function buildRecallQuery(context, keywords) {
        // 结合上下文和关键词构建更有效的搜索查询
        if (keywords.length > 0) {
            return `${context} ${keywords.join(' ')}`;
        }
        return context;
    }

    // 辅助函数：分类相关性
    function classifyRelevance(score) {
        if (score >= 0.8) return 'high';
        if (score >= 0.6) return 'medium';
        if (score >= 0.4) return 'low';
        return 'very_low';
    }

    // 辅助函数：构建回忆总结
    function buildRecallSummary(context, memories) {
        if (memories.length === 0) {
            return `基于当前上下文"${context.substring(0, 50)}..."，没有找到相关的历史记忆。`;
        }

        const memoryCount = memories.length;
        const avgRelevance = memories.reduce((sum, m) => sum + m.score, 0) / memoryCount;
        const relevanceLevel = classifyRelevance(avgRelevance);
        
        const tagSet = new Set();
        memories.forEach(memory => {
            memory.matchedTags.forEach(tag => tagSet.add(tag));
        });
        const topTags = Array.from(tagSet).slice(0, 5);

        return `基于当前上下文，系统主动回忆了 ${memoryCount} 个相关记忆（平均相关性：${relevanceLevel}）。` +
               (topTags.length > 0 ? ` 相关标签：${topTags.join('、')}` : '');
    }

    return vectorSearchRouter;
};