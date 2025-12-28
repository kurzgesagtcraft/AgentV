const plugin = require('./Plugin/VRChatOSC/VRChatOSC.js');

const config = {
    VRCHAT_OSC_HOST: '127.0.0.1',
    VRCHAT_OSC_PORT: 9000,
    VRCHAT_FACE_ADDRESS: '/avatar/parameters/FaceOSC',
    VRCHAT_ANIMATION_ADDRESS: '/avatar/parameters/VRCEmote',
    DebugMode: 'true'
};

plugin.initialize(config);

async function run() {
    console.log('Sending Wave animation via Plugin logic...');
    const result = await plugin.processToolCall({ 
        action_type: 'animation', 
        name: 'wave' 
    });
    console.log(result);
    
    // VRChat parameters often need to be reset to 0 to trigger again
    setTimeout(async () => {
        console.log('Resetting animation to 0...');
        const resetResult = await plugin.processToolCall({ 
            action_type: 'animation', 
            name: '0' 
        });
        console.log(resetResult);
        process.exit(0);
    }, 2000);
}

run();