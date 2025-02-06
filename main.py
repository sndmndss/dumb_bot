import os
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
    markets = await collect_markets()

    bid_side = "Bid"
    ask_side = "Ask"

    while True:

        for market in markets:
            symbol = market["symbol"]

            try:

                depth = await public.get_depth(symbol)
                bids = depth.get("bids", [])
                asks = depth.get("asks", [])

                if not bids or not asks:
                    logger.warning(f"[{symbol}] No bids/asks available, skipping...")
                    continue

                best_bid_price = bids[len(bids)//2][0]
                best_ask_price = asks[len(asks)//2][0]

                bid_order_price = best_ask_price
                ask_order_price = best_bid_price

                min_quantity = market["filters"]["quantity"]["minQuantity"]
                min_quantity_float = float(market["filters"]["quantity"]["minQuantity"])

                decimals = await get_decimal_places(min_quantity)

                random_val = random.uniform(min_quantity_float, min_quantity_float * 2)

                if float(min_quantity) < 1:
                    formated_random_step_size = f"{random_val:.{decimals}f}"
                else:
                    formated_random_step_size = int(random_val)

                await execute_order(account, symbol, bid_side, "Limit", "GTC", str(bid_order_price), str(formated_random_step_size))
                await execute_order(account, symbol, ask_side, "Limit", "GTC", str(ask_order_price), str(formated_random_step_size))

            except Exception as e:
                logger.exception(f"Error placing order on {symbol}: {e}")

        await asyncio.sleep(ORDER_INTERVAL_SECONDS)


async def execute_order(account: Account, symbol: str, side: str, order_type: str, time_in_force: str, price: str, quantity: str):
    response =  await account.execute_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        price=price,
        quantity=quantity,
        auto_lend_redeem=True
    )
    logger.info(
        f"[{symbol}] {side} order at {price} "
        f"(qty={quantity}) response: {response}"
    )
    return response


async def collect_markets():
    all_markets = await public.get_markets()
    if CONFIG_MARKET == "PERP":
        markets = [m for m in all_markets if m["marketType"] == MarketTypeEnum.PERP]
    elif CONFIG_MARKET == "SPOT":
        markets = [m for m in all_markets if m["marketType"] == MarketTypeEnum.SPOT]
    else:
        markets = [m for m in all_markets if
                   m["marketType"] == MarketTypeEnum.SPOT or m["marketType"] == MarketTypeEnum.PERP]
    logger.info(f"Found {len(markets)} markets.")
    return markets


if __name__ == "__main__":
    asyncio.run(main())
