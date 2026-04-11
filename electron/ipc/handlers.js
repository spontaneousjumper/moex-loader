const { ipcMain, dialog } = require("electron");

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
  });

  return result.filePaths[0];
});

ipcMain.handle("download-data", async (_, params) => {
  console.log("DOWNLOAD PARAMS:", params);

  // позже здесь будет логика MOEX + XLSX

  return { success: true };
});
