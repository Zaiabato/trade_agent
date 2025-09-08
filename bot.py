import time
import asyncio
from api_interface import HyperliquidAPI
from ml_strategy import MLStrategy
from telegram_alerts import send_alert
import logging

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

api = HyperliquidAPI()
ml = MLStrategy(testnet=True, grid_mode=False)  # Grid off по умолчанию; включи если нужно

def run_bot():
    while True:
        try:
            df = ml.fetch_historical_data(asset="BTC", interval="1h", lookback_hours=24)
            if not df.empty:
                df = ml.calculate_indicators(df)  # Уже в get_signal, но на всякий
                signal = ml.get_signal(df)
                logger.info(f"Сигнал: {signal}")
                price = api.get_price("BTC")
                if "BUY" in signal or "STRONG_BUY" in signal:
                    qty = 0.008  # Позже dynamic из risk
                    if "GRID_BUY" in signal:
                        for i in range(3):  # 3 grid levels с шагами 1%
                            grid_price = price * (1 + i * 0.01)
                            result = api.place_order("BTC", is_buy=True, qty=qty/3, price=grid_price)  # Limit orders
                            if result:
                                logger.info(f"Grid BUY level {i+1}: {result}")
                                asyncio.run(send_alert(f"Grid BUY level {i+1}: {result}"))
                                with open("trades.log", "a") as f:
                                    f.write(f"{time.ctime()},{result}\n")
                    else:
                        result = api.place_order("BTC", is_buy=True, qty=qty)
                        if result:
                            logger.info(f"BUY ордер: {result}")
                            asyncio.run(send_alert(f"Автоматический BUY ордер: {result}"))
                            with open("trades.log", "a") as f:
                                f.write(f"{time.ctime()},{result}\n")
                elif "SELL" in signal or "STRONG_SELL" in signal:
                    qty = 0.008
                    if "GRID_SELL" in signal:
                        for i in range(3):
                            grid_price = price * (1 - i * 0.01)  # -1% steps
                            result = api.place_order("BTC", is_buy=False, qty=qty/3, price=grid_price)
                            if result:
                                logger.info(f"Grid SELL level {i+1}: {result}")
                                asyncio.run(send_alert(f"Grid SELL level {i+1}: {result}"))
                                with open("trades.log", "a") as f:
                                    f.write(f"{time.ctime()},{result}\n")
                    else:
                        result = api.place_order("BTC", is_buy=False, qty=qty)
                        if result:
                            logger.info(f"SELL ордер: {result}")
                            asyncio.run(send_alert(f"Автоматический SELL ордер: {result}"))
                            with open("trades.log", "a") as f:
                                f.write(f"{time.ctime()},{result}\n")
                elif signal == "HOLD":
                    logger.info("Сигнал HOLD, ничего не делаем")
            else:
                logger.warning("Нет данных для сигнала")
            time.sleep(300)  # Проверка каждые 5 минут
        except Exception as e:
            logger.error(f"Ошибка в боте: {e}")
            time.sleep(60)

if __name__ == '__main__':
    run_bot()
