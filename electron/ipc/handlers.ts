import { ipcMain, dialog } from "electron";
import Store from "electron-store";
import { downloadData } from "../services/downloadService";
import { fetchTickers } from "../services/tickerService";

const store = new Store();

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
  });

  const folder = result.filePaths[0];

  if (folder) {
    store.set("downloadFolder", folder);
  }

  return folder;
});

ipcMain.handle("get-saved-folder", () => {
  return store.get("downloadFolder");
});

ipcMain.handle("download-data", async (_, params) => {
  if (!params.folder) {
    throw new Error("NO_FOLDER");
  }

  await downloadData(params);
  return { success: true };
});

ipcMain.handle("get-tickers", async () => {
  return await fetchTickers();
});
