import axios from "axios";
import { MoexResponse, MoexCandle } from "../types/moex";

const BASE_URL = "https://iss.moex.com/iss";

export async function fetchCandles(
  ticker: string,
  interval: number,
  from: string,
  to: string,
): Promise<MoexCandle[]> {
  let start = 0;
  let result: MoexCandle[] = [];

  while (true) {
    const response = await axios.get<MoexResponse>(
      `${BASE_URL}/engines/stock/markets/shares/securities/${ticker}/candles.json`,
      {
        params: {
          interval,
          from,
          till: to,
          start,
        },
      },
    );

    const chunk = response.data.candles.data;

    if (!chunk.length) break;

    result = result.concat(chunk);
    start += chunk.length;

    // защита от rate limit
    await new Promise((r) => setTimeout(r, 150));
  }

  return result;
}
