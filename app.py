import streamlit as st
import matplotlib.pyplot as plt
import asyncio
from api_interface import HyperliquidAPI
from ml_strategy import MLStrategy
from telegram_alerts import send_alert

st.title("Hyperliquid ML Trading Bot")

# Инициализация
api = HyperliquidAPI()
ml = MLStrategy(testnet=True)

# Получение исторических данных
df = ml.fetch_historical_data(symbol="BTC", interval="1h", lookback_days=7)
if not df.empty:
    df = ml.calculate_indicators(df)
    signal = ml.get_signal(df)
else:
    signal = "HOLD"

# Информация о счете и цене
price = api.get_price("BTC")
balance = api.get_balance()
positions = api.get_positions()

st.write(f"Текущая цена BTC: {price} USDC")
st.write(f"Баланс (выводимый): {balance.get('withdrawable', 0)} USDC")
st.write(f"Позиции: {positions}")
st.write(f"Сигнал ML: {signal}")

# График цены
if not df.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["time"], df["close"], label="BTC Close Price", color="#1f77b4")
    ax.plot(df["time"], df["SMA10"], label="SMA10", color="#ff7f0e")
    ax.plot(df["time"], df["SMA50"], label="SMA50", color="#2ca02c")
    ax.set_title("BTC Price with SMA10 and SMA50")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USDC)")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.write("Нет данных для построения графика")

# Кнопки ручного управления
if st.button("Отправить BUY ордер"):
    result = api.place_order("BTC", is_buy=True, qty=0.008)
    st.write(f"Результат BUY ордера: {result}")
    if result:
        asyncio.run(send_alert(f"BUY ордер отправлен: {result}"))

if st.button("Отправить SELL ордер"):
    result = api.place_order("BTC", is_buy=False, qty=0.008)
    st.write(f"Результат SELL ордера: {result}")
    if result:
        asyncio.run(send_alert(f"SELL ордер отправлен: {result}"))
