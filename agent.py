import time
import logging
import os
import threading
from api_interface import HyperliquidAPI
from ml_strategy import MLStrategy
from external_data import ExternalData
import telegram

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)
def send_telegram(msg):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram: {e}")

# Настройки
SYMBOL = "BTC"
TRADE_INTERVAL = 10  # секунд
POSITION_SIZE = 0.01

# Инициализация
api = HyperliquidAPI(testnet=True)
ml_strategy = MLStrategy()
external_data = ExternalData()

logger.info("Агент запущен")
send_telegram("🚀 Агент запущен на Hyperliquid testnet")

# Глобальная цена
current_price = None
def price_callback(price):
    global current_price
    current_price = price
    logger.info(f"Обновлённая цена {SYMBOL}: {price}")

# Запуск WebSocket
ws_thread = threading.Thread(target=api.subscribe_price, args=(SYMBOL, price_callback), daemon=True)
ws_thread.start()

# Главный цикл
try:
    while True:
        if current_price is None:
            time.sleep(1)
            continue
        last_price = current_price

        # Берём OHLCV
        df = api.info_client.ohlcv(symbol=SYMBOL, interval="1m", limit=20)
        if df.empty:
            logger.warning("Нет данных OHLCV")
            time.sleep(TRADE_INTERVAL)
            continue

        ext_features = external_data.get_features(SYMBOL)
        X_tensor = ml_strategy.prepare_data(df, ext_features)
        signal = ml_strategy.get_signal(X_tensor)
        logger.info(f"Сигнал: {signal}")

        positions = api.get_positions()
        open_pos = next((p for p in positions if p['symbol']==SYMBOL), None)

        if signal == "BUY" and (not open_pos or open_pos['side'] != 'BUY'):
            api.place_order(symbol=SYMBOL, is_buy=True, qty=POSITION_SIZE)
            send_telegram(f"🟢 BUY {POSITION_SIZE} {SYMBOL} по {last_price}")
        elif signal == "SELL" and (not open_pos or open_pos['side'] != 'SELL'):
            api.place_order(symbol=SYMBOL, is_buy=False, qty=POSITION_SIZE)
            send_telegram(f"🔴 SELL {POSITION_SIZE} {SYMBOL} по {last_price}")
        else:
            logger.info("HOLD — не открываем новые позиции")

        time.sleep(TRADE_INTERVAL)

except KeyboardInterrupt:
    logger.info("Агент остановлен вручную")
    send_telegram("⏹️ Агент остановлен вручную")
except Exception as e:
    logger.error(f"Ошибка в главном цикле: {e}")
    send_telegram(f"⚠️ Ошибка агента: {e}")
