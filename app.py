import streamlit as st
import matplotlib.pyplot as plt
from api_interface import HyperliquidAPI
from ml_strategy import MLStrategy
from telegram_alerts import send_alert
import asyncio
import pandas as pd
import time

st.title("Hyperliquid Trading Bot")

# Инициализация с grid_mode из UI
grid_mode = st.checkbox("Включить Grid Mode (для range-рынков)")
ml = MLStrategy(testnet=True, grid_mode=grid_mode)
api = HyperliquidAPI()

# Данные
df = ml.fetch_historical_data(asset="BTC", interval="1h", lookback_hours=24)
if not df.empty:
    df = ml.calculate_indicators(df)
    signal = ml.get_signal(df)
    st.write(f"Текущий сигнал (с LSTM и sentiment): {signal}")
else:
    signal = "HOLD"
    st.write("Нет данных для расчёта сигнала.")

# Цена и баланс
price = api.get_price("BTC")
balance = api.get_balance()
positions = api.get_positions()

# Расчёт PnL (твой старый код, но улучшен)
pnl = 0
for pos in positions:
    entry_price = float(pos.get("entryPx", 0))
    size = float(pos.get("sz", 0))
    side = pos.get("side")
    current_price = price
    if side == "buy":  # Long
        unrealized_pnl = (current_price - entry_price) * size
    else:  # Short
        unrealized_pnl = (entry_price - current_price) * size
    pnl += unrealized_pnl
st.write(f"Текущая цена BTC: {price} USDC")
st.write(f"Баланс (выводимый): {balance.get('withdrawable', 0)} USDC")
st.write(f"PnL: {pnl:.2f} USDC")
st.write(f"Позиции: {positions}")

# Загрузка логов сделок (твой старый, но улучшен парсинг — используй json позже)
trade_data = []
try:
    with open("trades.log", "r") as f:
        for line in f:
            timestamp, result = line.strip().split(",", 1)
            trade_time = pd.to_datetime(timestamp)
            # Упрощённый парсинг (улучши на json)
            if "buy" in result.lower():
                trade_price = price
            elif "sell" in result.lower():
                trade_price = price
            else:
                trade_price = price
            trade_data.append((trade_time, trade_price))
except FileNotFoundError:
    st.write("Файл trades.log не найден. Ожидайте автоматические сделки.")
except Exception as e:
    st.write(f"Ошибка чтения trades.log: {e}")

# График с отметками сделок
if not df.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["time"], df["close"], label="BTC Close Price", color="#1f77b4")
    ax.plot(df["time"], df["SMA10"], label="SMA10", color="#ff7f0e")
    ax.plot(df["time"], df["SMA50"], label="SMA50", color="#2ca02c")
    # Добавим BB для визуализации
    ax.plot(df["time"], df["BB_upper"], label="BB Upper", color="gray", linestyle="--")
    ax.plot(df["time"], df["BB_lower"], label="BB Lower", color="gray", linestyle="--")
    ax.fill_between(df["time"], df["BB_upper"], df["BB_lower"], alpha=0.2, color="gray")

    # Отметки сделок из trades.log
    trade_times = [t[0] for t in trade_data]
    trade_prices = [t[1] for t in trade_data]
    if trade_times and trade_prices:
        ax.scatter(trade_times, trade_prices, color="red", label="Trades", zorder=5)

    ax.set_title("BTC Price with Indicators, BB, and Trades (LSTM Signal: {signal})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USDC)")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.write("Нет данных для построения графика.")

# Ручное управление (твой старый, но добавь signal в алерты)
if st.button("Открыть BUY ордер"):
    result = api.place_order("BTC", is_buy=True, qty=0.008)
    st.write(f"Результат BUY ордера: {result}")
    if result:
        with open("trades.log", "a") as f:
            f.write(f"{time.ctime()},{result}\n")
        asyncio.create_task(send_alert(f"Ручной BUY ордер: {result} (signal: {signal})"))

if st.button("Закрыть BUY ордер"):
    for pos in positions:
        if pos.get("side") == "buy":
            result = api.cancel_order(pos.get("oid"), "BTC")
            st.write(f"Результат закрытия BUY ордера: {result}")
            if result:
                with open("trades.log", "a") as f:
                    f.write(f"{time.ctime()},{result}\n")
                asyncio.create_task(send_alert(f"Ручное закрытие BUY ордера: {result}"))

if st.button("Открыть SELL ордер"):
    result = api.place_order("BTC", is_buy=False, qty=0.008)
    st.write(f"Результат SELL ордера: {result}")
    if result:
        with open("trades.log", "a") as f:
            f.write(f"{time.ctime()},{result}\n")
        asyncio.create_task(send_alert(f"Ручной SELL ордер: {result} (signal: {signal})"))

if st.button("Закрыть SELL ордер"):
    for pos in positions:
        if pos.get("side") == "sell":
            result = api.cancel_order(pos.get("oid"), "BTC")
            st.write(f"Результат закрытия SELL ордера: {result}")
            if result:
                with open("trades.log", "a") as f:
                    f.write(f"{time.ctime()},{result}\n")
                asyncio.create_task(send_alert(f"Ручное закрытие SELL ордера: {result}"))
