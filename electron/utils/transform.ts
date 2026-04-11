import { app, BrowserWindow } from "electron";
import path from "path";
import { MoexCandle, TransformedCandle } from "../types/moex";

export function transformData(
  data: MoexCandle[],
  ticker: string,
  interval: number,
): TransformedCandle[] {
  return data.map((row) => {
    const [open, close, high, low, , volume, begin] = row;

    const date = new Date(begin);

    return {
      TICKER: ticker,
      PER: interval,
      DATE: date.toISOString().split("T")[0],
      TIME: date.toISOString().split("T")[1].split(".")[0],
      OPEN: open,
      HIGH: high,
      LOW: low,
      CLOSE: close,
      VOL: volume,
    };
  });
}
