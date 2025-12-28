// VRChatOSC.js (Hybrid Service Module)
const dgram = require('dgram');

let OSC_HOST;
let OSC_PORT;
let FACE_ADDRESS;
let ANIMATION_ADDRESS;
let DEBUG_MODE;

let client;
let pushVcpInfo = () => {};

/**
 * 简单的 OSC 消息构建器 (仅支持整数值)
 */
function buildOscMessage(address, value) {
    const addressLen = address.length + 1;
    const addressPad = (4 - (addressLen % 4)) % 4;
    const addressBuffer = Buffer.alloc(addressLen + addressPad);
    addressBuffer.write(address);

    let typeTag;
    let valueBuffer = Buffer.alloc(0);

    if (typeof value === 'boolean') {
        typeTag = value ? ",T" : ",F";
    } else if (!Number.isInteger(value)) {
        typeTag = ",f";
        valueBuffer = Buffer.alloc(4);
        valueBuffer.writeFloatBE(value);
    } else {
        typeTag = ",i";
        valueBuffer = Buffer.alloc(4);
        valueBuffer.writeInt32BE(value);
    }

    const typeTagLen = typeTag.length + 1;
    const typeTagPad = (4 - (typeTagLen % 4)) % 4;
    const typeTagBuffer = Buffer.alloc(typeTagLen + typeTagPad);
    typeTagBuffer.write(typeTag);

    return Buffer.concat([addressBuffer, typeTagBuffer, valueBuffer]);
}

function initialize(config, dependencies) {
    OSC_HOST = config.VRCHAT_OSC_HOST || '127.0.0.1';
    OSC_PORT = parseInt(config.VRCHAT_OSC_PORT || '9000', 10);
    FACE_ADDRESS = config.VRCHAT_FACE_ADDRESS || '/avatar/parameters/FaceOSC';
    ANIMATION_ADDRESS = config.VRCHAT_ANIMATION_ADDRESS || '/avatar/parameters/VRCEmote';
    DEBUG_MODE = String(config.DebugMode || 'false').toLowerCase() === 'true';

    client = dgram.createSocket('udp4');

    if (dependencies && dependencies.vcpLogFunctions && typeof dependencies.vcpLogFunctions.pushVcpInfo === 'function') {
        pushVcpInfo = dependencies.vcpLogFunctions.pushVcpInfo;
    }

    if (DEBUG_MODE) {
        console.log(`[VRChatOSC] Initialized. Host: ${OSC_HOST}, Port: ${OSC_PORT}`);
    }
}

function shutdown() {
    if (client) {
        client.close();
        if (DEBUG_MODE) console.log('[VRChatOSC] Socket closed.');
    }
}

async function processToolCall(args) {
    const { action_type, name, value: directValue, duration = 3.0 } = args;
    
    if (!action_type) {
        return { status: "error", error: "Missing 'action_type'." };
    }

    // 映射名称到数值 (参考 aiavatarkit)
    const faceMap = {
        "neutral": 0,
        "joy": 1,
        "angry": 2,
        "sorrow": 3,
        "fun": 4,
        "surprise": 5,
    };

    const animationMap = {
        "idling": 0,
        "wave": 1,
        "clap": 2,
        "point": 3,
        "cheer": 4,
        "dance": 5,
        "backflip": 6,
        "sadness": 7,
    };

    let address;
    let value;

    if (action_type === 'face') {
        address = FACE_ADDRESS;
        value = faceMap[name?.toLowerCase()];
        if (value === undefined) {
            const parsed = parseInt(name, 10);
            value = isNaN(parsed) ? undefined : parsed;
        }
    } else if (action_type === 'animation') {
        address = ANIMATION_ADDRESS;
        value = animationMap[name?.toLowerCase()];
        if (value === undefined) {
            const parsed = parseInt(name, 10);
            value = isNaN(parsed) ? undefined : parsed;
        }
    } else if (action_type === 'move') {
        // 移动控制：支持 Vertical, Horizontal, LookHorizontal 等
        const moveMap = {
            "forward": "/input/Vertical",
            "backward": "/input/Vertical",
            "left": "/input/Horizontal",
            "right": "/input/Horizontal",
            "lookleft": "/input/LookHorizontal",
            "lookright": "/input/LookHorizontal",
            "jump": "/input/Jump"
        };
        address = moveMap[name?.toLowerCase()] || name; // 如果不在 map 中，尝试直接作为地址
        
        // 处理移动数值
        if (directValue !== undefined) {
            value = parseFloat(directValue);
        } else {
            // 默认逻辑：forward=1, backward=-1 等
            const nameLower = name?.toLowerCase();
            if (nameLower === 'forward' || nameLower === 'right' || nameLower === 'lookright' || nameLower === 'jump') value = 1;
            else if (nameLower === 'backward' || nameLower === 'left' || nameLower === 'lookleft') value = -1;
            else value = 0;
        }
    } else if (action_type === 'parameter') {
        // 通用参数控制
        address = name.startsWith('/') ? name : `/avatar/parameters/${name}`;
        
        // 智能处理数值：优先处理 directValue，如果未定义则尝试解析 name (针对 AI 误传的情况)
        const rawValue = directValue !== undefined ? directValue : name;

        if (rawValue === 'true' || rawValue === true) {
            value = true;
        } else if (rawValue === 'false' || rawValue === false) {
            value = false;
        } else {
            const parsed = parseFloat(rawValue);
            if (!isNaN(parsed)) {
                value = Number.isInteger(parsed) ? parseInt(rawValue, 10) : parsed;
            } else {
                value = 1; // 默认触发
            }
        }
    } else {
        return { status: "error", error: `Invalid action_type: ${action_type}` };
    }

    if (value === undefined || (typeof value === 'number' && isNaN(value))) {
        return { status: "error", error: `Invalid name or value: ${name} (action_type: ${action_type})` };
    }

    try {
        const message = buildOscMessage(address, value);
        client.send(message, OSC_PORT, OSC_HOST, (err) => {
            if (err && DEBUG_MODE) console.error(`[VRChatOSC] Send error:`, err);
        });

        if (DEBUG_MODE) console.log(`[VRChatOSC] Sent ${address} -> ${value}`);

        // 广播到前端
        pushVcpInfo({
            type: 'VRCHAT_OSC_CONTROL',
            action_type,
            name,
            value,
            duration,
            timestamp: new Date().toISOString()
        });

        // 如果有持续时间，设定自动重置 (仅对表情有效，动作通常由 VRChat 自身逻辑处理或需要手动重置)
        if (duration > 0 && action_type === 'face') {
            setTimeout(() => {
                const resetMsg = buildOscMessage(address, 0); // 重置为 neutral (0)
                client.send(resetMsg, OSC_PORT, OSC_HOST);
                if (DEBUG_MODE) console.log(`[VRChatOSC] Reset ${address} to 0`);
            }, duration * 1000);
        }

        return { status: "success", result: `已向 VRChat 发送 ${action_type}: ${name} (${value})` };
    } catch (error) {
        return { status: "error", error: error.message };
    }
}

module.exports = {
    initialize,
    shutdown,
    processToolCall
};