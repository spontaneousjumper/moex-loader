export {};

declare global {
  interface Window {
    api: {
      selectFolder: () => Promise<string>;
      download: (params: DownloadParams) => Promise<{ success: boolean }>;
    };
  }

  interface DownloadParams {
    tickers: string[];
    interval: number;
    from: string;
    to: string;
    folder: string;
  }
}
