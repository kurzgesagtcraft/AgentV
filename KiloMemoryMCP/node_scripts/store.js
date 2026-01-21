
const fs = require('fs').promises;
const path = require('path');

async function main() {
    try {
        const args = JSON.parse(process.argv[2]);
        const { content, tags = [] } = args;
        
        const projectRoot = path.resolve(__dirname, '../..');
        const kbRoot = path.join(projectRoot, "dailynote");
        const memorySubdir = "KiloMemory";
        const memoryDir = path.join(kbRoot, memorySubdir);
        
        await fs.mkdir(memoryDir, { recursive: true });
        
        // 生成文件名
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const memoryId = require('crypto').createHash('md5').update(content).digest('hex').slice(0, 12);
        const filename = `KiloMemory_${timestamp}_${memoryId}.md`;
        const filepath = path.join(memoryDir, filename);
        
        // 构建Markdown内容
        const tagStr = tags.length > 0 ? tags.join(', ') : 'KiloMemory';
        const mdContent = `# Kilo Memory - ${new Date().toISOString()}

## 内容
${content}

## 元数据
- **记忆ID**: ${memoryId}
- **存储时间**: ${new Date().toISOString()}
- **标签**: ${tagStr}
- **来源**: KiloMemoryMCP

Tag: ${tagStr}
`;
        
        // 写入文件
        await fs.writeFile(filepath, mdContent, 'utf-8');
        
        console.log(JSON.stringify({
            success: true,
            memoryId: memoryId,
            filepath: filepath,
            message: "记忆已存储到VCP知识库"
        }));
        
    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message
        }));
    }
}

main();
