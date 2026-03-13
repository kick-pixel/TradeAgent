# API Integration Guide

Complete reference for integrating with RugCheck API, Bitget Wallet API, and supporting data sources.

## Table of Contents

- [Overview](#overview)
- [RugCheck API](#rugcheck-api)
- [Bitget Wallet API](#bitget-wallet-api)
- [Rate Limits](#rate-limits)
- [Error Handling](#error-handling)
- [Sample Responses](#sample-responses)
- [Configuration](#configuration)

---

## Overview

The Risk Scorer Skill integrates with multiple APIs to gather risk assessment data:

| API | Purpose | Auth Required |
|-----|---------|---------------|
| RugCheck | Token security analysis | API Key (free tier) |
| Bitget Wallet | Transaction history, holdings | API Key + Secret |
| Solana RPC | On-chain data queries | RPC Endpoint |
| Birdeye | Token prices, market data | API Key |

---

## RugCheck API

### Base URL

```
https://api.rugcheck.xyz/v1
```

### Authentication

```python
headers = {
    "Authorization": f"Bearer {RUGCHECK_API_KEY}",
    "Content-Type": "application/json"
}
```

### Endpoints

#### 1. Token Report

**Endpoint:** `GET /tokens/{mint}/report`

**Description:** Get comprehensive security report for a token.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mint` | string | Yes | Token mint address |

**Example:**
```bash
curl -X GET "https://api.rugcheck.xyz/v1/tokens/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/report" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Python Example:**
```python
import requests

def get_token_report(mint: str, api_key: str) -> dict:
    """Fetch token security report from RugCheck."""
    url = f"https://api.rugcheck.xyz/v1/tokens/{mint}/report"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

# Usage
report = get_token_report("TOKEN_MINT_ADDRESS", "YOUR_API_KEY")
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `mint` | string | Token mint address |
| `score` | number | Overall risk score (0-100) |
| `fileUri` | string | Report metadata URI |
| `name` | string | Token name |
| `symbol` | string | Token symbol |
| `authorities` | array | Contract authorities |
| `topHolders` | array | Top holder information |
| `markets` | array | Associated markets |

#### 2. Token Summary

**Endpoint:** `GET /tokens/{mint}/summary`

**Description:** Get simplified token summary.

**Example:**
```bash
curl -X GET "https://api.rugcheck.xyz/v1/tokens/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/summary"
```

#### 3. Pool Report

**Endpoint:** `GET /pools/{poolAddress}/report`

**Description:** Get liquidity pool security analysis.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `poolAddress` | string | Yes | LP pool address |

**Example:**
```python
def get_pool_report(pool_address: str, api_key: str) -> dict:
    """Fetch LP pool report."""
    url = f"https://api.rugcheck.xyz/v1/pools/{pool_address}/report"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()
```

#### 4. Batch Token Analysis

**Endpoint:** `POST /tokens/batch`

**Description:** Analyze multiple tokens in one request.

**Request Body:**
```json
{
  "mints": [
    "TOKEN_MINT_1",
    "TOKEN_MINT_2",
    "TOKEN_MINT_3"
  ]
}
```

**Example:**
```python
def batch_analyze_tokens(mints: list[str], api_key: str) -> list[dict]:
    """Analyze multiple tokens in batch."""
    url = "https://api.rugcheck.xyz/v1/tokens/batch"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"mints": mints}
    
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()
```

---

## Bitget Wallet API

### Base URLs

| Network | URL |
|---------|-----|
| Mainnet | `https://solana-mainnet.bitget.com` |
| Testnet | `https://solana-testnet.bitget.com` |

### Authentication

```python
import hmac
import hashlib
import time

def generate_bitget_signature(
    timestamp: str,
    method: str,
    path: str,
    body: str,
    secret_key: str
) -> str:
    """Generate Bitget API signature."""
    message = timestamp + method + path + body
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def get_headers(method: str, path: str, body: str = "") -> dict:
    """Generate authenticated Bitget headers."""
    timestamp = str(int(time.time() * 1000))
    signature = generate_bitget_signature(
        timestamp, method, path, body, BITGET_SECRET_KEY
    )
    
    return {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
```

### Endpoints

#### 1. Get Wallet Balance

**Endpoint:** `GET /api/v1/account/wallet-balance`

**Description:** Get all token balances for a wallet.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `walletAddress` | string | Yes | Wallet public key |

**Example:**
```python
import requests

def get_wallet_balance(wallet_address: str) -> dict:
    """Fetch wallet balance from Bitget."""
    path = "/api/v1/account/wallet-balance"
    params = {"walletAddress": wallet_address}
    
    headers = get_headers("GET", path)
    response = requests.get(
        f"https://solana-mainnet.bitget.com{path}",
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

**Sample Response:**
```json
{
  "code": "00000",
  "msg": "success",
  "data": {
    "walletAddress": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "balances": [
      {
        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "symbol": "USDC",
        "amount": "1500.500000",
        "decimals": 6
      },
      {
        "mint": "So11111111111111111111111111111111111111112",
        "symbol": "SOL",
        "amount": "12.450000000",
        "decimals": 9
      }
    ],
    "totalValueUsd": "4567.89"
  }
}
```

#### 2. Get Transaction History

**Endpoint:** `GET /api/v1/account/transactions`

**Description:** Get transaction history for a wallet.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `walletAddress` | string | Yes | - | Wallet public key |
| `startTime` | number | No | - | Start timestamp (ms) |
| `endTime` | number | No | - | End timestamp (ms) |
| `limit` | number | No | 50 | Max results (1-100) |
| `offset` | number | No | 0 | Pagination offset |

**Example:**
```python
def get_transaction_history(
    wallet_address: str,
    start_time: int = None,
    end_time: int = None,
    limit: int = 50
) -> dict:
    """Fetch transaction history from Bitget."""
    path = "/api/v1/account/transactions"
    params = {
        "walletAddress": wallet_address,
        "limit": limit
    }
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time
    
    headers = get_headers("GET", path)
    response = requests.get(
        f"https://solana-mainnet.bitget.com{path}",
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

**Sample Response:**
```json
{
  "code": "00000",
  "msg": "success",
  "data": {
    "transactions": [
      {
        "signature": "5xKX...signature",
        "timestamp": 1710345600000,
        "type": "transfer",
        "status": "confirmed",
        "from": "SenderWallet123...",
        "to": "ReceiverWallet456...",
        "amount": "100.000000",
        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "fee": "0.000005"
      }
    ],
    "hasMore": true,
    "total": 156
  }
}
```

#### 3. Get Token Holdings

**Endpoint:** `GET /api/v1/account/token-holdings`

**Description:** Get detailed token holdings with percentages.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `walletAddress` | string | Yes | Wallet public key |

**Example:**
```python
def get_token_holdings(wallet_address: str) -> dict:
    """Fetch token holdings with distribution."""
    path = "/api/v1/account/token-holdings"
    params = {"walletAddress": wallet_address}
    
    headers = get_headers("GET", path)
    response = requests.get(
        f"https://solana-mainnet.bitget.com{path}",
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

**Sample Response:**
```json
{
  "code": "00000",
  "msg": "success",
  "data": {
    "walletAddress": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "holdings": [
      {
        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "symbol": "USDC",
        "amount": "5000.000000",
        "valueUsd": "5000.00",
        "percentage": 45.5
      },
      {
        "mint": "So11111111111111111111111111111111111111112",
        "symbol": "SOL",
        "amount": "25.000000000",
        "valueUsd": "3500.00",
        "percentage": 31.8
      },
      {
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "symbol": "BONK",
        "amount": "100000000.000000",
        "valueUsd": "2500.00",
        "percentage": 22.7
      }
    ],
    "totalValueUsd": "11000.00"
  }
}
```

#### 4. Get DEX Interactions

**Endpoint:** `GET /api/v1/analytics/dex-interactions`

**Description:** Get DEX trading activity for a wallet.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `walletAddress` | string | Yes | Wallet public key |
| `days` | number | No | Lookback period (default: 30) |

**Example:**
```python
def get_dex_interactions(wallet_address: str, days: int = 30) -> dict:
    """Fetch DEX interaction history."""
    path = "/api/v1/analytics/dex-interactions"
    params = {
        "walletAddress": wallet_address,
        "days": days
    }
    
    headers = get_headers("GET", path)
    response = requests.get(
        f"https://solana-mainnet.bitget.com{path}",
        headers=headers,
        params=params,
        timeout=60
    )
    response.raise_for_status()
    return response.json()
```

**Sample Response:**
```json
{
  "code": "00000",
  "msg": "success",
  "data": {
    "walletAddress": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "period": "30d",
    "interactions": [
      {
        "dex": "Raydium",
        "poolAddress": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        "tokenIn": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "tokenOut": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "amountIn": "100.000000",
        "amountOut": "5000000.000000",
        "timestamp": 1710345600000,
        "txSignature": "3xKX...signature"
      }
    ],
    "summary": {
      "totalSwaps": 45,
      "totalVolumeUsd": "15000.00",
      "uniquePools": 12,
      "mostTradedToken": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    }
  }
}
```

---

## Rate Limits

### RugCheck API

| Tier | Requests/Minute | Requests/Day | Features |
|------|-----------------|--------------|----------|
| Free | 10 | 500 | Basic reports |
| Pro | 60 | 10,000 | Full reports, batch |
| Enterprise | 300 | Unlimited | Priority, custom |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1710345660
```

### Bitget Wallet API

| Endpoint | Rate Limit |
|----------|------------|
| Balance queries | 30 req/min |
| Transaction history | 20 req/min |
| Token holdings | 30 req/min |
| DEX interactions | 15 req/min |

**Rate Limit Response:**
```json
{
  "code": "10001",
  "msg": "Rate limit exceeded. Please retry after 60 seconds."
}
```

### Handling Rate Limits

```python
import time
from functools import wraps

def rate_limit(max_calls: int, period: int):
    """Rate limiting decorator."""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls
            calls[:] = [t for t in calls if now - t < period]
            
            if len(calls) >= max_calls:
                sleep_time = period - (now - calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=10, period=60)
def call_rugcheck_api(mint: str) -> dict:
    """Rate-limited RugCheck call."""
    # Implementation...
```

---

## Error Handling

### Error Codes

#### RugCheck API Errors

| Code | Message | Action |
|------|---------|--------|
| 400 | Invalid mint address | Verify address format |
| 401 | Unauthorized | Check API key |
| 404 | Token not found | Token may not exist |
| 429 | Rate limited | Implement backoff |
| 500 | Server error | Retry with backoff |

#### Bitget API Errors

| Code | Message | Action |
|------|---------|--------|
| 00000 | Success | - |
| 10001 | Rate limit exceeded | Wait and retry |
| 10002 | Invalid signature | Regenerate signature |
| 10003 | Invalid API key | Check credentials |
| 10004 | Request expired | Check timestamp |
| 20001 | Wallet not found | Verify address |
| 20002 | No data available | Wallet may be empty |

### Retry Logic

```python
import time
from requests.exceptions import RequestException

class APIError(Exception):
    """Custom API error class."""
    def __init__(self, message: str, code: str = None, status_code: int = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """Retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            
            # Check if retryable
            status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            
            if status_code in [429, 500, 502, 503, 504]:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)
            else:
                raise
    
    return None

# Usage
def fetch_token_data(mint: str) -> dict:
    """Fetch token data with retry."""
    def _fetch():
        response = requests.get(f"{BASE_URL}/tokens/{mint}/report", timeout=30)
        response.raise_for_status()
        return response.json()
    
    return retry_with_backoff(_fetch)
```

### Error Response Handling

```python
def handle_api_response(response: requests.Response) -> dict:
    """Handle API response and raise appropriate errors."""
    if response.status_code == 200:
        data = response.json()
        
        # Check for API-specific error codes
        if "code" in data and data["code"] != "00000":
            raise APIError(
                message=data.get("msg", "Unknown error"),
                code=data.get("code"),
                status_code=response.status_code
            )
        return data
    
    # HTTP error handling
    error_messages = {
        400: "Bad request - invalid parameters",
        401: "Unauthorized - invalid API key",
        403: "Forbidden - insufficient permissions",
        404: "Resource not found",
        429: "Rate limit exceeded",
        500: "Internal server error",
        502: "Bad gateway",
        503: "Service unavailable",
        504: "Gateway timeout"
    }
    
    raise APIError(
        message=error_messages.get(response.status_code, "Unknown error"),
        status_code=response.status_code
    )
```

---

## Sample Responses

### Complete Token Report (RugCheck)

```json
{
  "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "score": 15,
  "risks": [],
  "fileUri": "https://arweave.net/abc123",
  "name": "USD Coin",
  "symbol": "USDC",
  "decimals": 6,
  "description": "Fully backed stablecoin",
  "image": "https://assets.rugcheck.xyz/usdc.png",
  "metadata": {
    "tokenType": "SPL",
    "supply": "32500000000",
    "isStablecoin": true
  },
  "topHolders": [
    {
      "address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
      "balance": "5000000000",
      "percentage": 15.38,
      "owner": "Binance"
    }
  ],
  "markets": [
    {
      "pubkey": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
      "marketType": "AMM",
      "baseMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "quoteMint": "So11111111111111111111111111111111111111112",
      "liquidity": "50000000",
      "volume24h": "2500000"
    }
  ],
  "authorities": {
    "mint": null,
    "freeze": null
  }
}
```

### High Risk Token Report

```json
{
  "mint": "RISKY123456789ABCDEF",
  "score": 85,
  "risks": [
    {
      "name": "Mint authority enabled",
      "level": "critical",
      "description": "Mint authority is still enabled. Developer can create unlimited tokens."
    },
    {
      "name": "LP unlocked",
      "level": "high",
      "description": "Liquidity pool is not locked and can be removed at any time."
    },
    {
      "name": "Concentrated holders",
      "level": "high",
      "description": "Top 10 holders control 78% of supply."
    }
  ],
  "topHolders": [
    {
      "address": "DEV_WALLET_123",
      "balance": "500000000",
      "percentage": 50.0,
      "owner": "Unknown"
    }
  ],
  "markets": [
    {
      "pubkey": "POOL_123",
      "liquidity": "5000",
      "volume24h": "500"
    }
  ],
  "authorities": {
    "mint": "DEV_WALLET_123",
    "freeze": "DEV_WALLET_123"
  }
}
```

### Wallet Risk Analysis Response

```json
{
  "walletAddress": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "riskScore": 35,
  "riskLevel": "MEDIUM",
  "factors": [
    {
      "name": "wallet_age",
      "score": 10,
      "detail": "Wallet created 45 days ago"
    },
    {
      "name": "token_concentration",
      "score": 15,
      "detail": "60% in high-risk meme tokens"
    },
    {
      "name": "dex_activity",
      "score": 10,
      "detail": "15 swaps in last 7 days"
    }
  ],
  "flags": ["high_meme_exposure", "frequent_new_tokens"],
  "holdings": {
    "totalValueUsd": "5000.00",
    "tokenCount": 8,
    "topHoldings": [
      {"symbol": "SOL", "percentage": 40},
      {"symbol": "BONK", "percentage": 35},
      {"symbol": "WIF", "percentage": 25}
    ]
  },
  "transactionStats": {
    "totalTx": 156,
    "last24h": 12,
    "avgValueUsd": "250.00"
  },
  "recommendation": "PROCEED_WITH_CAUTION - Medium risk wallet"
}
```

---

## Configuration

### Environment Variables

```bash
# RugCheck API
RUGCHECK_API_KEY=your_rugcheck_api_key

# Bitget Wallet API
BITGET_API_KEY=your_bitget_api_key
BITGET_SECRET_KEY=your_bitget_secret
BITGET_PASSPHRASE=your_bitget_passphrase

# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Optional: Birdeye for additional data
BIRDEYE_API_KEY=your_birdeye_api_key
```

### Configuration File

```yaml
# config/risk_scorer.yaml
api:
  rugcheck:
    base_url: "https://api.rugcheck.xyz/v1"
    api_key: "${RUGCHECK_API_KEY}"
    timeout: 30
    max_retries: 3
  
  bitget:
    base_url: "https://solana-mainnet.bitget.com"
    api_key: "${BITGET_API_KEY}"
    secret_key: "${BITGET_SECRET_KEY}"
    passphrase: "${BITGET_PASSPHRASE}"
    timeout: 30
    max_retries: 3

rate_limits:
  rugcheck:
    requests_per_minute: 10
    burst: 5
  
  bitget:
    requests_per_minute: 30
    burst: 10

caching:
  enabled: true
  ttl_seconds: 3600  # 1 hour
  max_entries: 1000

log_level: INFO
```

### Loading Configuration

```python
import os
import yaml
from pathlib import Path

def load_config(config_path: str = "config/risk_scorer.yaml") -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    # Expand environment variables
    def expand_env(obj):
        if isinstance(obj, str) and obj.startswith("${"):
            env_var = obj[2:-1]
            return os.environ.get(env_var, obj)
        elif isinstance(obj, dict):
            return {k: expand_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_env(v) for v in obj]
        return obj
    
    return expand_env(config)

# Usage
config = load_config()
rugcheck_key = config['api']['rugcheck']['api_key']
```
