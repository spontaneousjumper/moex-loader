import axios from "axios";

export async function fetchTickers(): Promise<string[]> {
  const res = await axios.get(
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json",
    {
      params: {
        "securities.columns": "SECID",
      },
    },
  );

  const tickers: string[] = res.data.securities.data.map(
    (row: [string]) => row[0],
  );

  return Array.from(new Set(tickers)).sort();
}
