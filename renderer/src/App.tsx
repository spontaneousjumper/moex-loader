import {
  Button,
  DatePicker,
  Input,
  Layout,
  List,
  Progress,
  Select,
  Typography,
  message,
  Card,
  ConfigProvider,
} from "antd";
import ruRU from "antd/locale/ru_RU";
import { useEffect, useMemo, useState } from "react";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

dayjs.tz.setDefault("Europe/Moscow");

const { RangePicker } = DatePicker;
const { Title } = Typography;
const { Sider, Content } = Layout;

const INTERVAL_OPTIONS = [
  { value: 1, label: "1 минута" },
  { value: 10, label: "10 минут" },
  { value: 60, label: "1 час" },
  { value: 24, label: "1 день" },
];

function App() {
  const [allTickers, setAllTickers] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);

  const [dates, setDates] = useState<[Dayjs, Dayjs] | null>(null);
  const [interval, setInterval] = useState<number>(24);
  const [folder, setFolder] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    window.api.getTickers().then((data) => setAllTickers(data ?? []));

    // загрузка сохранённой папки
    window.api.getSavedFolder?.().then((f: string) => {
      if (f) setFolder(f);
    });

    const unsubProgress = window.api.onProgress((p) => {
      setProgress(Math.round((p.current / p.total) * 100));
    });

    const unsubLog = window.api.onLog((log) => {
      setLogs((prev) => [
        `${new Date().toLocaleTimeString()} — ${log.message}`,
        ...prev,
      ]);
    });

    return () => {
      unsubProgress();
      unsubLog();
    };
  }, []);

  const filteredTickers = useMemo(() => {
    const q = search.toLowerCase();
    return allTickers.filter((t) => t.toLowerCase().includes(q));
  }, [allTickers, search]);

  const sortedTickers = useMemo(() => {
    const selected = new Set(tickers);
    return [...filteredTickers].sort(
      (a, b) => Number(selected.has(b)) - Number(selected.has(a)),
    );
  }, [filteredTickers, tickers]);

  const toggleTicker = (ticker: string) => {
    setTickers((prev) =>
      prev.includes(ticker)
        ? prev.filter((t) => t !== ticker)
        : [...prev, ticker],
    );
  };

  const handleSelectFolder = async () => {
    const result = await window.api.selectFolder();
    if (result) setFolder(result);
  };

  const disabledDate = (current: Dayjs) => {
    return current && current > dayjs().tz("Europe/Moscow");
  };

  const validate = () => {
    if (!tickers.length) return message.warning("Выбери тикеры");
    if (!dates) return message.warning("Выбери даты");
    if (!folder) return message.warning("Выбери папку");

    return true;
  };

  const handleDownload = async () => {
    if (!validate()) return;

    setLogs([]);
    setProgress(0);
    setLoading(true);

    try {
      await window.api.download({
        tickers,
        interval,
        from: dates![0].tz("Europe/Moscow").format("YYYY-MM-DD HH:mm"),
        to: dates![1].tz("Europe/Moscow").format("YYYY-MM-DD HH:mm"),
        folder,
      });

      message.success("Готово");
    } catch {
      message.error("Ошибка");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfigProvider locale={ruRU}>
      <Layout style={{ height: "100vh" }}>
        <Sider width={300} style={{ background: "#111", padding: 12 }}>
          <Title level={5} style={{ color: "#fff" }}>
            Тикеры
          </Title>

          <Input
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ marginBottom: 10 }}
          />

          <List
            size="small"
            dataSource={sortedTickers}
            style={{ height: "80vh", overflow: "auto" }}
            renderItem={(item) => {
              const selected = tickers.includes(item);

              return (
                <List.Item
                  onClick={() => toggleTicker(item)}
                  style={{
                    cursor: "pointer",
                    padding: "6px 10px",
                    borderLeft: selected
                      ? "3px solid #1677ff"
                      : "3px solid transparent",
                    background: selected ? "#1f1f1f" : "transparent",
                  }}
                >
                  <span
                    style={{
                      color: selected ? "#fff" : "#aaa",
                      fontFamily: "monospace",
                    }}
                  >
                    {item}
                  </span>
                </List.Item>
              );
            }}
          />
        </Sider>

        <Layout>
          <Content style={{ padding: 16 }}>
            <Card>
              <Title level={4}>Параметры</Title>

              <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
                <RangePicker
                  showTime={{ format: "HH:mm" }}
                  format="DD.MM.YYYY HH:mm"
                  placeholder={["Начало", "Конец"]}
                  disabledDate={disabledDate}
                  onChange={(v) => setDates(v as [Dayjs, Dayjs])}
                  style={{ flex: 1 }}
                />

                <Select
                  options={INTERVAL_OPTIONS}
                  value={interval}
                  onChange={setInterval}
                  style={{ width: 150 }}
                />
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                <Button onClick={handleSelectFolder}>
                  {folder || "Выбрать папку"}
                </Button>

                <Button
                  type="primary"
                  loading={loading}
                  disabled={!folder}
                  onClick={handleDownload}
                >
                  Скачать ({tickers.length})
                </Button>
              </div>
            </Card>

            <Card style={{ marginTop: 16 }}>
              <Progress percent={progress} />
            </Card>

            <Card style={{ marginTop: 16 }}>
              <Title level={5}>Логи</Title>
              <List
                size="small"
                dataSource={logs}
                style={{ maxHeight: 250, overflow: "auto" }}
                renderItem={(item) => <List.Item>{item}</List.Item>}
              />
            </Card>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
