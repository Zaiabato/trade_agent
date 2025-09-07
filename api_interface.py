import os
import logging
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

class HyperliquidAPI:
    def __init__(self):
        logging.basicConfig(
            filename='trades.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        load_dotenv()
        self.private_key = os.getenv("PRIVATE_KEY")
        self.account_address = os.getenv("ACCOUNT_ADDRESS")
        self.api_key = os.getenv("API_KEY")
        self.api_secret = os.getenv("API_SECRET")
        self.environment = os.getenv("ENVIRONMENT", "testnet")

        self.base_url = constants.TESTNET_API_URL if self.environment == "testnet" else constants.MAINNET_API_URL

        try:
            self.account = Account.from_key(self.private_key)
            if self.account.address.lower() != self.account_address.lower():
                self.logger.error("PRIVATE_KEY не соответствует ACCOUNT_ADDRESS")
                raise ValueError("PRIVATE_KEY не соответствует ACCOUNT_ADDRESS")
            self.info_client = Info(self.base_url, skip_ws=True)
            self.exchange_client = Exchange(
                wallet=self.account,
                base_url=self.base_url,
                account_address=self.account_address
            )
            self.logger.info(f"Подключено к Hyperliquid {'testnet' if self.environment == 'testnet' else 'mainnet'}")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации API: {e}")
            raise

    def get_price(self, symbol="BTC"):
        try:
            all_mids = self.info_client.all_mids()
            price = float(all_mids.get(symbol, 0))
            self.logger.info(f"Получена цена для {symbol}: {price}")
            return price
        except Exception as e:
            self.logger.error(f"Ошибка получения цены для {symbol}: {e}")
            return 0

    def place_order(self, symbol="BTC", is_buy=True, qty=0.01, price=None):
        try:
            meta = self.info_client.meta()
            universe = meta['universe']
            self.logger.info(f"Доступные активы: {[u['name'] for u in universe]}")
            if symbol not in [u['name'] for u in universe]:
                self.logger.error(f"Символ {symbol} не найден в universe")
                return None

            order_type = {"market": {}} if price is None else {"limit": {"tif": "Gtc"}}
            limit_px = str(price) if price else "0"
            sz = str(qty)
            self.logger.info(f"Отправка ордера: coin={symbol}, is_buy={is_buy}, sz={sz}, limit_px={limit_px}, order_type={order_type}")
            result = self.exchange_client.order(
                coin=symbol,
                is_buy=is_buy,
                sz=sz,
                limit_px=limit_px,
                order_type=order_type,
                reduce_only=False
            )
            self.logger.info(f"Размещён ордер: {symbol}, {'buy' if is_buy else 'sell'}, qty={qty}, type={order_type}")
            return result
        except Exception as e:
            self.logger.error(f"Ошибка размещения ордера: {e}")
            return None

    def cancel_order(self, order_id, symbol="BTC"):
        try:
            result = self.exchange_client.cancel_order(coin=symbol, oid=order_id)
            self.logger.info(f"Отменён ордер: {order_id} для {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Ошибка отмены ордера: {e}")
            return None

    def get_balance(self):
        try:
            user_state = self.info_client.user_state(self.account_address)
            balance = {
                "margin_used": user_state.get("marginUsed", "0"),
                "withdrawable": user_state.get("withdrawable", "0"),
                "asset_positions": user_state.get("assetPositions", [])
            }
            self.logger.info(f"Получен баланс: {balance}")
            return balance
        except Exception as e:
            self.logger.error(f"Ошибка получения баланса: {e}")
            return {}

    def get_positions(self):
        try:
            user_state = self.info_client.user_state(self.account_address)
            positions = user_state.get("assetPositions", [])
            self.logger.info(f"Получены позиции: {positions}")
            return positions
        except Exception as e:
            self.logger.error(f"Ошибка получения позиций: {e}")
            return []
