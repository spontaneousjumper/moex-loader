import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("api", {
  selectFolder: () => ipcRenderer.invoke("select-folder"),
  getSavedFolder: () => ipcRenderer.invoke("get-saved-folder"),

  download: (params: any) => ipcRenderer.invoke("download-data", params),

  getTickers: () => ipcRenderer.invoke("get-tickers"),

  onProgress: (callback: any) => {
    const listener = (_: any, data: any) => callback(data);
    ipcRenderer.on("progress", listener);

    return () => ipcRenderer.removeListener("progress", listener);
  },

  onLog: (callback: any) => {
    const listener = (_: any, data: any) => callback(data);
    ipcRenderer.on("log", listener);

    return () => ipcRenderer.removeListener("log", listener);
  },
});
