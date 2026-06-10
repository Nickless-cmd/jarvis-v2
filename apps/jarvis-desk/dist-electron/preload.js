"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Preload — eneste bro mellem renderer og main process.
 *
 * Vi udsætter et MINIMALT API via contextBridge. Renderer kan ikke
 * tilgå Node.js, ipcRenderer eller noget andet uden via dette API.
 */
const electron_1 = require("electron");
const bridge = {
    config: {
        get: () => electron_1.ipcRenderer.invoke('config:get'),
        set: (cfg) => electron_1.ipcRenderer.invoke('config:set', cfg),
    },
    platform: process.platform,
};
electron_1.contextBridge.exposeInMainWorld('jarvisDesk', bridge);
