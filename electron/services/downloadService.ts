import { fetchCandles } from "./moexService";
import { transformData } from "../utils/transform";
import { saveToXlsx } from "./xlsxService";

interface Params {
  tickers: string[];
  interval: number;
  from: string;
  to: string;
  folder: string;
}

export async function downloadData(params: Params) {
  const { tickers, interval, from, to, folder } = params;

  for (const ticker of tickers) {
    console.log(`Loading ${ticker}...`);

    const raw = await fetchCandles(ticker, interval, from, to);
    const transformed = transformData(raw, ticker, interval);

    saveToXlsx(transformed, folder, ticker);

    console.log(`Saved ${ticker}`);
  }
}
