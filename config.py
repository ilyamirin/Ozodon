"""Central configuration for the Ozodon application.

Values are read from environment variables with safe defaults for local
development. For production, set variables explicitly to avoid surprises.
"""
import os

# Database configuration
MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME: str = "ozodon"

# Hub mode controls whether hub routes/UI are enabled
HUB_MODE: bool = os.getenv("HUB_MODE", "false").lower() == "true"
HUB_NAME: str = os.getenv("HUB_NAME", "Ozodon Node")
HUB_DOMAIN: str = os.getenv("HUB_DOMAIN", "https://your-ozodon-instance.com")
HUB_DESCRIPTION: str = os.getenv("HUB_DESCRIPTION", "A federated marketplace node")

# TON blockchain integration (keys may be empty in local dev)
TON_API_KEY: str = os.getenv("TON_API_KEY", "")
# Split mnemonic safely into a list; empty string -> []
TON_WALLET_MNEMONIC: list[str] = os.getenv("TON_WALLET_MNEMONIC", "").split()

# Path to the registry of hubs that this node may replicate to
HUBS_FILE: str = "hubs.json"
