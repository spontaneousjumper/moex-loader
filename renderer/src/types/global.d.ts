export {};

declare global {
  interface DownloadParams {
    tickers: string[];
    interval: number;
    from: string;
    to: string;
    folder: string;
  }

  interface ProgressEvent {
    current: number;
    total: number;
    ticker: string;
  }

  interface LogEvent {
    message: string;
  }

  interface Ticker {
    secid: string;
    name: string;
  }
  interface Window {
    api: {
      selectFolder: () => Promise<string>;
      getSavedFolder: () => Promise<string>;
      download: (params: DownloadParams) => Promise<{ success: boolean }>;
      getTickers: () => Promise<Ticker[]>;

      onProgress: (callback: (data: ProgressEvent) => void) => () => void;
      onLog: (callback: (data: LogEvent) => void) => () => void;
    };
  }
}
