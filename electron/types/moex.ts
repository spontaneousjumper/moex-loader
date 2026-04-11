export type MoexCandle = [
  open: number,
  close: number,
  high: number,
  low: number,
  value: number,
  volume: number,
  begin: string,
];

export interface MoexResponse {
  candles: {
    data: MoexCandle[];
  };
}

export interface TransformedCandle {
  TICKER: string;
  PER: number;
  DATE: string;
  TIME: string;
  OPEN: number;
  HIGH: number;
  LOW: number;
  CLOSE: number;
  VOL: number;
}
