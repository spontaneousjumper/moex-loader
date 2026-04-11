const { app, BrowserWindow } = require("electron");
const path = require("path");

require("./ipc/handlers");

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
    },
  });

  const url = process.env.ELECTRON_START_URL;

  if (url) {
    win.loadURL(url);
  } else {
    win.loadFile(path.join(__dirname, "../renderer/dist/index.html"));
  }
}

app.whenReady().then(createWindow);
