import { fetchCandles } from "./moexService";
import { transformData } from "../utils/transform";
import { saveToXlsx } from "./xlsxService";
import { BrowserWindow } from "electron";

interface Params {
  tickers: string[];
  interval: number;
  from: string;
  to: string;
  folder: string;
}

function send(channel: string, payload: any) {
  const win = BrowserWindow.getAllWindows()[0];
  win?.webContents.send(channel, payload);
}

export async function downloadData(params: Params) {
  const { tickers, interval, from, to, folder } = params;

  const total = tickers.length;
  let current = 0;

  for (const ticker of tickers) {
    current++;

    send("log", { message: `Загрузка ${ticker}...` });

    try {
      const raw = await fetchCandles(ticker, interval, from, to);
      const transformed = transformData(raw, ticker, interval);

      saveToXlsx(transformed, folder, ticker);

      send("log", { message: `Готово: ${ticker}` });
    } catch (e) {
      send("log", { message: `Ошибка: ${ticker}` });
    }

    send("progress", {
      current,
      total,
      ticker,
    });
  }

  send("log", { message: "Все тикеры обработаны" });
}
