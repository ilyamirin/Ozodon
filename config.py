# config.py
import os

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "ozodon"

TON_API_KEY = os.getenv("TON_API_KEY", "")
TON_WALLET_MNEMONIC = os.getenv("TON_WALLET_MNEMONIC", "").split()
HUB_URL = os.getenv("HUB_URL", "https://hub.fedmarket.example")