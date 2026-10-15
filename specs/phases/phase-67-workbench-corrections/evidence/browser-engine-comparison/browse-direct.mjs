import {runDriverDaemon} from './browse-current/node_modules/browse/dist/lib/driver/daemon/server.js';
await runDriverDaemon({session:'owned',target:{kind:'cdp',endpoint:process.argv[2]}});
