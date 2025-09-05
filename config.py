# config.py
import os

# База
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "ozodon"

# Режим хаба
HUB_MODE = os.getenv("HUB_MODE", "false").lower() == "true"
HUB_NAME = os.getenv("HUB_NAME", "Ozodon Node")
HUB_DOMAIN = os.getenv("HUB_DOMAIN", "https://your-ozodon-instance.com")
HUB_DESCRIPTION = os.getenv("HUB_DESCRIPTION", "A federated marketplace node")

# TON
TON_API_KEY = os.getenv("TON_API_KEY", "")
TON_WALLET_MNEMONIC = os.getenv("TON_WALLET_MNEMONIC", "").split()

# Реестр хабов
HUBS_FILE = "hubs.json"
