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

  interface Window {
    api: {
      selectFolder: () => Promise<string>;
      download: (params: DownloadParams) => Promise<{ success: boolean }>;
      getTickers: () => Promise<string[]>;

      onProgress: (callback: (data: ProgressEvent) => void) => () => void;
      onLog: (callback: (data: LogEvent) => void) => () => void;
    };
  }
}
