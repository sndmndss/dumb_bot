import os
import time
import random
import asyncio
from decimal import Decimal

from loguru import logger

from bpx.async_.account import Account
from bpx.async_.public import Public

from bpx.constants.enums import MarketTypeEnum

from config import load_config

# logger
os.makedirs("logs", exist_ok=True)
logger.add("logs/bot_{time}.log", rotation="1 day", compression="zip", level="INFO")

# config
config = load_config()
CONFIG_MARKET = config["config_market"]
ORDER_INTERVAL_SECONDS = config["order_interval_seconds"]
SWITCH_SIDE_INTERVAL_SECONDS = config["switch_side_interval_seconds"]
account = Account(config["public_key"], config["secret_key"])
public = Public()

# helper functions
def get_full_float(step_size_str: str) -> float:

    value_decimal = Decimal(step_size_str)
    value_float = float(value_decimal)
    return value_float


async def get_decimal_places(s: str):
    if '.' in s:
        return len(s.split('.')[1]) if s.split('.')[1][0] != '0' or len(s.split('.')[1]) > 1 else 0
    return 0


# main trading loop
async def main():
    all_markets = await public.get_markets()
    if CONFIG_MARKET == "PERP":
        markets = [m for m in all_markets if m["marketType"] == MarketTypeEnum.PERP]
    elif CONFIG_MARKET == "SPOT":
        markets = [m for m in all_markets if m["marketType"] == MarketTypeEnum.SPOT]
    else:
        markets = [m for m in all_markets if m["marketType"] == MarketTypeEnum.SPOT or m["marketType"] == MarketTypeEnum.PERP]
    logger.info(f"Found {len(markets)} markets.")

    current_side = "Bid"
    last_switch_time = time.time()

    while True:
        now = time.time()

        if now - last_switch_time >= SWITCH_SIDE_INTERVAL_SECONDS:
            current_side = "Ask" if current_side == "Bid" else "Bid"
            last_switch_time = now
            logger.info(f"Side switched to {current_side} at {time.ctime()}.")

        for market in markets:
            symbol = market["symbol"]

            try:
                balances = await account.get_balances()

                token = (symbol.split("_"))[0]
                depth = await public.get_depth(symbol)
                bids = depth.get("bids", [])
                asks = depth.get("asks", [])

                if not bids or not asks:
                    logger.warning(f"[{symbol}] No bids/asks available, skipping...")
                    continue
                if current_side == "Ask" and "PERP" not in symbol:
                    if not balances.get(token):
                        logger.warning(f"[{symbol}] No balance available, skipping...")
                        continue

                best_bid_price = bids[len(bids)//2][0]
                best_ask_price = asks[len(asks)//2][0]

                if current_side == "Bid":
                    order_price = best_ask_price
                else:
                    order_price = best_bid_price

                min_quantity = market["filters"]["quantity"]["minQuantity"]
                min_quantity_float = float(market["filters"]["quantity"]["minQuantity"])
                decimals = await get_decimal_places(min_quantity)
                if current_side == "Bid" or "PERP" in symbol:
                    random_val = random.uniform(min_quantity_float, min_quantity_float * 2)
                elif current_side == "Ask":
                    available_quantity = balances[token]["available"]
                    random_val = random.uniform(min_quantity_float, float(available_quantity))
                if float(min_quantity) < 1:
                    formated_random_step_size = f"{random_val:.{decimals}f}"
                else:
                    formated_random_step_size = int(random_val)
                order_response = await account.execute_order(
                    symbol=symbol,
                    side=current_side,
                    order_type="Limit",
                    time_in_force="GTC",
                    price=str(order_price),
                    quantity=formated_random_step_size,
                    auto_lend_redeem=True
                )
                logger.info(
                    f"[{symbol}] {current_side} order at {order_price} "
                    f"(qty={formated_random_step_size}) response: {order_response}"
                )
                message = order_response.get("message", "")
                if message == "Insufficient funds":
                    current_side = "Ask" if current_side == "Bid" else "Bid"
                    last_switch_time = now
                    logger.info(f"Side switched to {current_side} at {time.ctime()}.")

            except Exception as e:
                logger.exception(f"Error placing order on {symbol}: {e}")

        await asyncio.sleep(ORDER_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
