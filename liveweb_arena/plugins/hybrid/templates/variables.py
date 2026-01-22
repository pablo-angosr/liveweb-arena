"""Variables for hybrid cross-site query templates"""

import random
from dataclasses import dataclass
from typing import List


@dataclass
class CryptoSpec:
    """Specification for a cryptocurrency"""
    coin_id: str      # CoinGecko API ID
    symbol: str       # Trading symbol
    name: str         # Display name


@dataclass
class StockSpec:
    """Specification for a stock"""
    symbol: str       # Stooq symbol (e.g., "aapl.us")
    ticker: str       # Common ticker (e.g., "AAPL")
    name: str         # Display name


# Major cryptocurrencies with stable CoinGecko IDs
CRYPTOS: List[CryptoSpec] = [
    CryptoSpec("bitcoin", "BTC", "Bitcoin"),
    CryptoSpec("ethereum", "ETH", "Ethereum"),
    CryptoSpec("solana", "SOL", "Solana"),
    CryptoSpec("ripple", "XRP", "XRP"),
    CryptoSpec("cardano", "ADA", "Cardano"),
    CryptoSpec("dogecoin", "DOGE", "Dogecoin"),
    CryptoSpec("polkadot", "DOT", "Polkadot"),
    CryptoSpec("avalanche-2", "AVAX", "Avalanche"),
    CryptoSpec("chainlink", "LINK", "Chainlink"),
    CryptoSpec("litecoin", "LTC", "Litecoin"),
    CryptoSpec("near", "NEAR", "NEAR Protocol"),
    CryptoSpec("uniswap", "UNI", "Uniswap"),
    CryptoSpec("bittensor", "TAO", "Bittensor"),
    CryptoSpec("render-token", "RENDER", "Render"),
    CryptoSpec("aave", "AAVE", "Aave"),
]

# Major US stocks available on Stooq
STOCKS: List[StockSpec] = [
    StockSpec("aapl.us", "AAPL", "Apple"),
    StockSpec("msft.us", "MSFT", "Microsoft"),
    StockSpec("googl.us", "GOOGL", "Alphabet"),
    StockSpec("amzn.us", "AMZN", "Amazon"),
    StockSpec("nvda.us", "NVDA", "NVIDIA"),
    StockSpec("meta.us", "META", "Meta"),
    StockSpec("tsla.us", "TSLA", "Tesla"),
    StockSpec("jpm.us", "JPM", "JPMorgan Chase"),
    StockSpec("v.us", "V", "Visa"),
    StockSpec("wmt.us", "WMT", "Walmart"),
    StockSpec("ko.us", "KO", "Coca-Cola"),
    StockSpec("dis.us", "DIS", "Disney"),
    StockSpec("nke.us", "NKE", "Nike"),
    StockSpec("intc.us", "INTC", "Intel"),
    StockSpec("amd.us", "AMD", "AMD"),
]


class CryptoVariable:
    """Variable for cryptocurrency selection"""

    def __init__(self, cryptos: List[CryptoSpec] = None):
        self.cryptos = cryptos or CRYPTOS

    def sample(self, rng: random.Random) -> CryptoSpec:
        return rng.choice(self.cryptos)


class StockVariable:
    """Variable for stock selection"""

    def __init__(self, stocks: List[StockSpec] = None):
        self.stocks = stocks or STOCKS

    def sample(self, rng: random.Random) -> StockSpec:
        return rng.choice(self.stocks)
