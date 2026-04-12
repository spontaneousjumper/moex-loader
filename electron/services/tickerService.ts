import axios from "axios";

export type Ticker = {
  secid: string;
  name: string;
};

export async function fetchTickers(): Promise<Ticker[]> {
  const res = await axios.get(
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json",
    {
      params: {
        "securities.columns": "SECID,SHORTNAME",
      },
    },
  );

  const rows = res.data.securities.data;

  return rows.map((row: any) => ({
    secid: row[0],
    name: row[1],
  }));
}
