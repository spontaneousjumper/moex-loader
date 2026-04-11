import {
  Button,
  DatePicker,
  Select,
  Space,
  Typography,
  message,
  Card,
} from "antd";
import { useState } from "react";
import type { Dayjs } from "dayjs";

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const TICKER_OPTIONS = [
  { value: "SBER", label: "SBER" },
  { value: "GAZP", label: "GAZP" },
  { value: "LKOH", label: "LKOH" },
];

const INTERVAL_OPTIONS = [
  { value: 1, label: "1 минута" },
  { value: 10, label: "10 минут" },
  { value: 60, label: "1 час" },
  { value: 24, label: "1 день" },
];

function App() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [dates, setDates] = useState<[Dayjs, Dayjs] | null>(null);
  const [interval, setInterval] = useState<number>(24);
  const [folder, setFolder] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const handleSelectFolder = async () => {
    try {
      const result = await window.api.selectFolder();
      if (result) {
        setFolder(result);
      }
    } catch (e) {
      message.error("Ошибка выбора папки");
    }
  };

  const validate = (): boolean => {
    if (!tickers.length) {
      message.warning("Выбери хотя бы один тикер");
      return false;
    }

    if (!dates) {
      message.warning("Выбери диапазон дат");
      return false;
    }

    if (!folder) {
      message.warning("Выбери папку для сохранения");
      return false;
    }

    return true;
  };

  const handleDownload = async () => {
    if (!validate()) return;

    setLoading(true);

    try {
      await window.api.download({
        tickers,
        interval,
        from: dates![0].format("YYYY-MM-DD"),
        to: dates![1].format("YYYY-MM-DD"),
        folder,
      });

      message.success("Данные успешно выгружены");
    } catch (e) {
      console.error(e);
      message.error("Ошибка при загрузке данных");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, display: "flex", justifyContent: "center" }}>
      <Card style={{ width: 500 }}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Title level={3}>MOEX Data Loader</Title>

          <div>
            <Text>Тикеры</Text>
            <Select
              mode="multiple"
              placeholder="Выбери тикеры"
              options={TICKER_OPTIONS}
              value={tickers}
              onChange={setTickers}
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <Text>Диапазон дат</Text>
            <RangePicker
              style={{ width: "100%" }}
              onChange={(values) => setDates(values as [Dayjs, Dayjs])}
            />
          </div>

          <div>
            <Text>Интервал</Text>
            <Select
              options={INTERVAL_OPTIONS}
              value={interval}
              onChange={setInterval}
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <Text>Папка сохранения</Text>
            <Button block onClick={handleSelectFolder}>
              {folder || "Выбрать папку"}
            </Button>
          </div>

          <Button
            type="primary"
            block
            loading={loading}
            onClick={handleDownload}
          >
            Скачать данные
          </Button>
        </Space>
      </Card>
    </div>
  );
}

export default App;
