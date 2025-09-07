import os
from dotenv import load_dotenv
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from eth_account import Account
import logging

logging.basicConfig(
    filename='trades.log',  # Используем trades.log для сделок
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HyperliquidAPI:
    def __init__(self):
        load_dotenv()
        self.private_key = os.getenv("PRIVATE_KEY")
        self.account_address = os.getenv("ACCOUNT_ADDRESS")
        self.environment = os.getenv("ENVIRONMENT", "testnet")

        self.base_url = constants.TESTNET_API_URL if self.environment == "testnet" else constants.MAINNET_API_URL

        self.account = Account.from_key(self.private_key)
        self.info_client = Info(self.base_url, skip_ws=True)
        self.exchange_client = Exchange(
            wallet=self.account,
            base_url=self.base_url,
            account_address=self.account_address
        )
        logger.info(f"Подключено к Hyperliquid {'testnet' if self.environment == 'testnet' else 'mainnet'}")

    def get_price(self, asset="BTC"):
        try:
            all_mids = self.info_client.all_mids()
            return float(all_mids.get(asset, 0))
        except Exception as e:
            logger.error(f"Ошибка получения цены для {asset}: {e}")
            return 0

    def place_order(self, asset="BTC", is_buy=True, qty=0.008, price=None):
        try:
            order_type = {"market": {}} if price is None else {"limit": {"tif": "Gtc"}}
            limit_px = str(price) if price else "0"
            logger.info(f"Отправка ордера: asset={asset}, is_buy={is_buy}, sz={qty}, limit_px={limit_px}, order_type={order_type}")
            result = self.exchange_client.order(
                asset=asset,  # Изменено с coin на asset
                is_buy=is_buy,
                sz=str(qty),
                limit_px=limit_px,
                order_type=order_type
            )
            logger.info(f"Размещён ордер: {asset}, {'buy' if is_buy else 'sell'}, qty={qty}, result={result}")
            return result
        except Exception as e:
            logger.error(f"Ошибка размещения ордера: {e}")
            return None

    def cancel_order(self, order_id, asset="BTC"):
        try:
            result = self.exchange_client.cancel_order(asset=asset, oid=order_id)
            logger.info(f"Отменён ордер: {order_id} для {asset}, result={result}")
            return result
        except Exception as e:
            logger.error(f"Ошибка отмены ордера: {e}")
            return None

    def get_balance(self):
        try:
            user_state = self.info_client.user_state(self.account_address)
            balance = {
                "margin_used": user_state.get("marginUsed", "0"),
                "withdrawable": user_state.get("withdrawable", "0"),
                "asset_positions": user_state.get("assetPositions", [])
            }
            logger.info(f"Получен баланс: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return {}

    def get_positions(self):
        try:
            user_state = self.info_client.user_state(self.account_address)
            positions = user_state.get("assetPositions", [])
            logger.info(f"Получены позиции: {positions}")
            return positions
        except Exception as e:
            logger.error(f"Ошибка получения позиций: {e}")
            return []
