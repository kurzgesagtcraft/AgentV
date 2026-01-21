const WebSocket = require('ws');

const VCP_Key = 'vcp123456';
const PORT = 6005;
const wsUrl = `ws://localhost:${PORT}/VCPlog/VCP_Key=${VCP_Key}`;

console.log(`Testing WebSocket connection to: ${wsUrl}`);

const ws = new WebSocket(wsUrl);

ws.on('open', () => {
    console.log('WebSocket connection opened successfully!');
    ws.send(JSON.stringify({ type: 'test', message: 'Hello from test client' }));
});

ws.on('message', (data) => {
    console.log('Received message:', data.toString());
});

ws.on('close', (code, reason) => {
    console.log(`WebSocket closed. Code: ${code}, Reason: ${reason}`);
});

ws.on('error', (error) => {
    console.error('WebSocket error:', error.message);
});

// Close after 5 seconds
setTimeout(() => {
    ws.close();
    process.exit(0);
}, 5000);