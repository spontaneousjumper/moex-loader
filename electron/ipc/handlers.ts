import { ipcMain, dialog } from "electron";
import { downloadData } from "../services/downloadService";

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
  });

  return result.filePaths[0];
});

ipcMain.handle("download-data", async (_, params) => {
  try {
    await downloadData(params);
    return { success: true };
  } catch (e) {
    console.error(e);
    return { success: false };
  }
});
