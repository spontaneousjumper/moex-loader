import { app, BrowserWindow, globalShortcut, Menu } from "electron";
import path from "path";

require("./ipc/handlers");

function createWindow() {
  Menu.setApplicationMenu(null);

  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
    },
  });

  const url = process.env.ELECTRON_START_URL ?? "http://localhost:5173";

  console.log("DEV URL:", url);

  const isDev = process.env.NODE_ENV !== "production";

  if (isDev) {
    win.loadURL(url);
  } else {
    win.loadFile(path.join(__dirname, "../renderer/dist/index.html"));
  }

  globalShortcut.register("F12", () => {
    win.webContents.openDevTools();
  });
}

app.whenReady().then(createWindow);
