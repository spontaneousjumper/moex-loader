import * as XLSX from "xlsx";
import path from "path";
import { TransformedCandle } from "../types/moex";

export function saveToXlsx(
  data: TransformedCandle[],
  folder: string,
  ticker: string,
) {
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(workbook, worksheet, "Data");

  const filePath = path.join(folder, `${ticker}.xlsx`);
  XLSX.writeFile(workbook, filePath);
}
