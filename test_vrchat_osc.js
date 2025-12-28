const dgram = require('dgram');

// 模拟 VRChatOSC.js 中的 buildOscMessage 函数
function buildOscMessage(address, value) {
    const addressLen = address.length + 1;
    const addressPad = (4 - (addressLen % 4)) % 4;
    const addressBuffer = Buffer.alloc(addressLen + addressPad);
    addressBuffer.write(address);

    const typeTag = ",i";
    const typeTagLen = typeTag.length + 1;
    const typeTagPad = (4 - (typeTagLen % 4)) % 4;
    const typeTagBuffer = Buffer.alloc(typeTagLen + typeTagPad);
    typeTagBuffer.write(typeTag);

    const valueBuffer = Buffer.alloc(4);
    valueBuffer.writeInt32BE(value);

    return Buffer.concat([addressBuffer, typeTagBuffer, valueBuffer]);
}

const OSC_HOST = '127.0.0.1';
const OSC_PORT = 9000;
const client = dgram.createSocket('udp4');

const testCases = [
    { address: '/avatar/parameters/FaceOSC', value: 1, label: 'Face: Joy' },
    { address: '/avatar/parameters/VRCEmote', value: 1, label: 'Animation: Wave' }
];

async function runTests() {
    for (const test of testCases) {
        console.log(`Testing ${test.label}...`);
        const message = buildOscMessage(test.address, test.value);
        client.send(message, OSC_PORT, OSC_HOST, (err) => {
            if (err) {
                console.error(`Error sending ${test.label}:`, err);
            } else {
                console.log(`Successfully sent ${test.label} to ${OSC_HOST}:${OSC_PORT}`);
            }
        });
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    client.close();
    console.log('Tests completed.');
}

runTests();