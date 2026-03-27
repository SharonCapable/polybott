import requests

POLYMARKET_API = "https://gamma-api.polymarket.com"

def get_open_markets(limit=100):
    try:
        resp = requests.get(
            f"{POLYMARKET_API}/markets",
            params={"closed": "false", "active": "true", "limit": limit},
            timeout=10
        )
        resp.raise_for_status()
        markets = resp.json()

        cleaned = []
        for m in markets:
            # outcomePrices is a JSON string like '["0.73", "0.27"]'
            raw_prices = m.get("outcomePrices", "[]")
            try:
                if isinstance(raw_prices, str):
                    import json
                    prices = json.loads(raw_prices)
                else:
                    prices = raw_prices
                yes_price = float(prices[0]) if prices else 0.5
            except Exception:
                yes_price = 0.5

            cleaned.append({
                "id": m.get("id"),
                "question": m.get("question", ""),
                "description": m.get("description", "")[:200],
                "yes_price": yes_price,
                "volume": m.get("volume", 0),
            })

        return cleaned

    except Exception as e:
        print(f"[scanner] Error fetching markets: {e}")
        return []


if __name__ == "__main__":
    markets = get_open_markets()
    print(f"Found {len(markets)} open markets\n")
    for m in markets[:10]:
        print(f"  Q: {m['question']}")
        print(f"     YES price: {m['yes_price']} | Volume: ${m['volume']}")
        print()