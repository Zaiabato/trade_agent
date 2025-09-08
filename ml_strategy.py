import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
import pandas_ta as ta  # Для Chop indicator
from api_interface import HyperliquidAPI
from hyperliquid.utils import constants
import logging
import time
from datetime import datetime, timedelta

load_dotenv()  # Загружаем .env для BACKTESTING_START/END

class MLStrategy:
    def __init__(self, testnet=True, grid_mode=False):
        logging.basicConfig(
            filename='ml_strategy.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("MLStrategy инициализирован")  # Test-log: Запишет при создании объекта
        self.model = None
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.api = HyperliquidAPI()
        self.scaler = MinMaxScaler()
        self.lstm_model = self._build_lstm()
        self.is_grid_mode = grid_mode
        self.chop_threshold = 50  # Threshold для ranging market (из algogene.com)

    def _build_lstm(self):
        """Построить простую LSTM-модель для предсказаний цен."""
        class LSTMPredictor(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(input_size=1, hidden_size=50, num_layers=1, batch_first=True)
                self.linear = nn.Linear(50, 1)

            def forward(self, x):
                _, (hn, _) = self.lstm(x)
                return self.linear(hn[-1])

        model = LSTMPredictor()
        return model

    def fetch_historical_data(self, asset="BTC", interval="1h", lookback_hours=24):
        """Получить реальные исторические данные. Используем env dates для timeshift."""
        try:
            start_date = os.getenv("BACKTESTING_START", "2025-01-01")
            end_date = os.getenv("BACKTESTING_END", datetime.now().strftime("%Y-%m-%d"))
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            start_ts = end_ts - (lookback_hours * 3600 * 1000)
            candles = self.api.get_candles(coin=asset, interval=interval, start_time=start_ts, end_time=end_ts)
            
            if candles and len(candles) > 0:
                df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "volume"])
                df["time"] = pd.to_datetime(df["time"], unit="ms").dt.strftime('%Y-%m-%d %H:%M:%S')  # Format как строка
                df = df.sort_values("time").reset_index(drop=True)
                
                user_state = self.api.get_balance()
                funding_rate = float(user_state.get("fundingRate", 0)) if "fundingRate" in user_state else 0.0001
                df["funding_rate"] = funding_rate
                
                self.logger.info(f"Загружены реальные данные для {asset}: {len(df)} свечей с env dates {start_date} to {end_date}")
                return df
            else:
                self.logger.warning("Нет реальных данных, fallback на синтетику")
                return self._generate_synthetic(asset, lookback_hours)
        except Exception as e:
            self.logger.error(f"Ошибка получения данных: {e}. Fallback на синтетику.")
            return self._generate_synthetic(asset, lookback_hours)

    def _generate_synthetic(self, asset="BTC", lookback_hours=24):
        """Fallback: Генерируем синтетические данные с форматированным timestamp."""
        try:
            current_price = self.api.get_price(asset)
            if current_price == 0:
                self.logger.error("Не удалось получить цену для синтетики")
                return pd.DataFrame()
            times = pd.date_range(end=pd.to_datetime("now"), periods=lookback_hours, freq="1h")  # Фикс: "1h" вместо "1H"
            prices = np.random.normal(current_price, current_price * 0.01, lookback_hours)
            df = pd.DataFrame({
                "time": times.dt.strftime('%Y-%m-%d %H:%M:%S'),  # Format как строка
                "open": prices,
                "high": prices * 1.005,
                "low": prices * 0.995,
                "close": prices,
                "volume": np.random.randint(100, 1000, lookback_hours)
            })
            df["funding_rate"] = 0.0001
            self.logger.info(f"Сгенерированы синтетические данные для {asset}: {len(df)} точек")
            return df
        except Exception as e:
            self.logger.error(f"Ошибка генерации синтетики: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df):
        try:
            if df.empty:
                return df
            df["SMA10"] = df["close"].rolling(window=10, min_periods=1).mean()
            df["SMA50"] = df["close"].rolling(window=50, min_periods=1).mean()
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))
            df["SMA20"] = df["close"].rolling(window=20, min_periods=1).mean()
            df["BB_upper"] = df["SMA20"] + (df["close"].rolling(window=20, min_periods=1).std() * 2)
            df["BB_lower"] = df["SMA20"] - (df["close"].rolling(window=20, min_periods=1).std() * 2)
            # Chop indicator для grid (из algogene.com)
            df["chop"] = ta.chop(df["high"], df["low"], df["close"], length=14)
            self.logger.info("Индикаторы рассчитаны: SMA, RSI, BB, Chop")
            return df
        except Exception as e:
            self.logger.error(f"Ошибка расчёта индикаторов: {e}")
            return df

    def get_sentiment(self, asset="BTC"):
        """Получить sentiment (заглушка; позже NLP)."""
        try:
            sentiment_score = 0.5  # Bullish
            self.logger.info(f"Sentiment для {asset}: {sentiment_score}")
            return sentiment_score
        except Exception as e:
            self.logger.error(f"Ошибка sentiment: {e}")
            return 0.0

    def get_signal(self, df):
        try:
            if df.empty or len(df) < 50:
                self.logger.warning("Данные недостаточны, сигнал HOLD")
                return "HOLD"
            
            df = self.calculate_indicators(df)
            last_row = df.iloc[-1]
            
            # Базовый сигнал SMA/RSI
            base_signal = "HOLD"
            if last_row["SMA10"] > last_row["SMA50"] and last_row["RSI"] < 70:
                base_signal = "BUY"
            elif last_row["SMA10"] < last_row["SMA50"] and last_row["RSI"] > 30:
                base_signal = "SELL"
            
            # LSTM с train/test split (80/20, чтобы избежать overfitting как в paperswithbacktest.com)
            lstm_signal = "HOLD"
            if len(df) > 100:
                prices = pd.to_numeric(df["close"], errors='coerce').dropna().values.reshape(-1, 1)
                if len(prices) > 20:  # Min для split
                    split_idx = int(len(prices) * 0.8)  # 80% train
                    train_prices = prices[:split_idx]
                    test_prices = prices[split_idx:]
                    scaled_train = self.scaler.fit_transform(train_prices)
                    # Простой pred на last 10 из test (упрощённо, без full train loop)
                    seq_length = 10
                    if len(test_prices) >= seq_length:
                        seq = self.scaler.transform(test_prices[-seq_length:].reshape(-1, 1)).reshape(1, seq_length, 1)
                        seq_tensor = torch.tensor(seq, dtype=torch.float32)
                        self.lstm_model.eval()
                        with torch.no_grad():
                            pred_scaled = self.lstm_model(seq_tensor).item()
                        pred_price = self.scaler.inverse_transform([[pred_scaled]])[0][0]
                        current_price = last_row["close"]
                        if pred_price > current_price * 1.001:
                            lstm_signal = "BUY"
                        elif pred_price < current_price * 0.999:
                            lstm_signal = "SELL"
                        self.logger.info(f"LSTM предсказание (split 80/20): {pred_price:.2f} vs {current_price:.2f} -> {lstm_signal}")
            else:
                self.logger.warning("Недостаточно данных для LSTM")
            
            sentiment = self.get_sentiment()
            signal = base_signal
            if lstm_signal != "HOLD" and lstm_signal == base_signal:
                signal = lstm_signal  # Усиление
            if sentiment > 0.3 and signal == "BUY":
                signal = "STRONG_BUY"
            elif sentiment < -0.3 and signal == "SELL":
                signal = "STRONG_SELL"
            
            # Grid mode: Если chop > threshold (ranging market)
            chop_value = last_row["chop"] if "chop" in last_row else 0
            if (self.is_grid_mode or chop_value > self.chop_threshold) and abs(last_row["close"] - last_row["SMA50"]) / last_row["SMA50"] > 0.02:
                signal = f"GRID_{signal}" if signal != "HOLD" else "HOLD"
                self.logger.info(f"Grid активирован (chop={chop_value:.2f}): {signal}")
            
            # Учёт funding rate
            if last_row["funding_rate"] < 0 and signal == "BUY":
                signal = "HOLD"
            
            self.logger.info(f"Финальный сигнал: {signal}, base={base_signal}, lstm={lstm_signal}, sentiment={sentiment}, chop={chop_value:.2f}")
            return signal
        except Exception as e:
            self.logger.error(f"Ошибка генерации сигнала: {e}")
            return "HOLD"
