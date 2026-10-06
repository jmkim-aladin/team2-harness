import {startStaticServer, parseArgs} from './runtime/node_modules/@openhands/agent-canvas/scripts/static-server.mjs';
const config=parseArgs(['--host','127.0.0.1','--port','18760','--dir',process.env.CANVAS_BUILD_DIR,'--disable-telemetry']);
config.sessionApiKey=process.env.LOCAL_BACKEND_API_KEY;
for (const route of ['/api','/sockets','/server_info','/health','/ready','/alive','/docs','/openapi.json']) config.routes[route]='http://127.0.0.1:18763';
config.rejectPrefixes=['/api/automation'];
startStaticServer(config);
