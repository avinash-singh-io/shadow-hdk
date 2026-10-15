import {runDriverDaemon} from './browse-current/node_modules/browse/dist/lib/driver/daemon/server.js';
await runDriverDaemon({session:'owned',target:{kind:'managed-local',headless:true,chromeArgs:['--disable-background-networking']}});
