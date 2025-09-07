import numpy as np
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants
import logging

class MLStrategy:
    def __init__(self, testnet=True):
        logging.basicConfig(
            filename='ml_strategy.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.model = None  # Позже можно загрузить PyTorch модель
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info_client = Info(self.base_url, skip_ws=True)

    def fetch_historical_data(self, symbol="BTC", interval="1h", lookback_days=30):
        """Получение исторических данных OHLCV"""
        try:
            import time
            end_time = int(time.time() * 1000)
            start_time = end_time - lookback_days * 24 * 60 * 60 * 1000
            candles = self.info_client.candles(
                coin=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "volume"])
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
            self.logger.info(f"Получены исторические данные для {symbol}: {len(df)} свечей")
            return df
        except Exception as e:
            self.logger.error(f"Ошибка получения исторических данных: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df):
        """Простейшие индикаторы без pandas_ta"""
        try:
            df["SMA10"] = df["close"].rolling(10).mean()
            df["SMA50"] = df["close"].rolling(50).mean()
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))
            self.logger.info("Индикаторы рассчитаны: SMA10, SMA50, RSI")
            return df
        except Exception as e:
            self.logger.error(f"Ошибка расчёта индикаторов: {e}")
            return df

    def get_signal(self, df):
        """Логика сигналов на основе индикаторов"""
        try:
            if df.empty:
                self.logger.warning("Данные отсутствуют, сигнал HOLD")
                return "HOLD"
            last_row = df.iloc[-1]
            if last_row["SMA10"] > last_row["SMA50"] and last_row["RSI"] < 70:
                self.logger.info("Сигнал BUY: SMA10 > SMA50 и RSI < 70")
                return "BUY"
            elif last_row["SMA10"] < last_row["SMA50"] and last_row["RSI"] > 30:
                self.logger.info("Сигнал SELL: SMA10 < SMA50 и RSI > 30")
                return "SELL"
            else:
                self.logger.info("Сигнал HOLD")
                return "HOLD"
        except Exception as e:
            self.logger.error(f"Ошибка генерации сигнала: {e}")
            return "HOLD"
