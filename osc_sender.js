const dgram = require('dgram');

function buildOscMessage(address, value) {
    const addressLen = address.length + 1;
    const addressPad = (4 - (addressLen % 4)) % 4;
    const addressBuffer = Buffer.alloc(addressLen + addressPad);
    addressBuffer.write(address);

    const type = process.argv[4] || (Number.isInteger(value) ? 'i' : 'f');
    const typeTag = "," + type;
    const typeTagLen = typeTag.length + 1;
    const typeTagPad = (4 - (typeTagLen % 4)) % 4;
    const typeTagBuffer = Buffer.alloc(typeTagLen + typeTagPad);
    typeTagBuffer.write(typeTag);

    const valueBuffer = Buffer.alloc(4);
    if (type === 'f') {
        valueBuffer.writeFloatBE(value);
    } else if (type === 'i') {
        valueBuffer.writeInt32BE(value);
    } else if (type === 'b') {
        // Boolean in OSC is often just the type tag 'T' or 'F' with no payload,
        // but some implementations use 4-byte int 0/1.
        // VRChat expects type tag 'T' or 'F' for Bool.
    }

    if (type === 'T' || type === 'F') {
        return Buffer.concat([addressBuffer, typeTagBuffer]);
    }
    return Buffer.concat([addressBuffer, typeTagBuffer, valueBuffer]);
}

const address = process.argv[2];
const rawValue = process.argv[3];
const type = process.argv[4] || (rawValue.includes('.') ? 'f' : 'i');

let value;
if (type === 'f') value = parseFloat(rawValue);
else if (type === 'i') value = parseInt(rawValue, 10);
else if (type === 'T' || type === 'F') value = null;

const host = '127.0.0.1';
const port = 9000;

const client = dgram.createSocket('udp4');
const message = buildOscMessage(address, value);

client.send(message, port, host, (err) => {
    if (err) {
        console.error('Error:', err);
    } else {
        console.log(`Sent ${address} -> ${value} to ${host}:${port}`);
    }
    client.close();
});