import requests
import json
import os
import time
import anthropic
from dotenv import load_dotenv

load_dotenv()

POLYMARKET_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_market_cache = []
_cache_timestamp = 0
CACHE_TTL = 600

HARD_MEME_FILTER = [
    "jesus christ", "bigfoot", "alien invasion",
    "time travel", "immortal", "never die"
]

# GTA VI is fine to keep now — it's actually liquid and tradeable
# We were too aggressive filtering it


def fetch_all_markets(limit=200) -> list[dict]:
    """
    Fetch from multiple endpoints to get full market coverage.
    Gamma API = market metadata
    Events API = sports, politics, structured events
    """
    global _market_cache, _cache_timestamp

    now = time.time()
    if _market_cache and (now - _cache_timestamp) < CACHE_TTL:
        print(f"  [agent] Using cached {len(_market_cache)} markets")
        return _market_cache

    all_markets = []

    # Source 1: Standard markets endpoint
    try:
        resp = requests.get(
            f"{POLYMARKET_API}/markets",
            params={
                "closed": "false",
                "active": "true",
                "limit": limit,
            },
            timeout=10
        )
        resp.raise_for_status()
        all_markets.extend(resp.json())
        print(f"  [agent] Markets endpoint: {len(resp.json())} raw")
    except Exception as e:
        print(f"  [agent] Markets endpoint error: {e}")

    # Source 2: Events endpoint — this is where sports/politics live
    try:
        resp2 = requests.get(
            f"{POLYMARKET_API}/events",
            params={
                "closed": "false",
                "active": "true",
                "limit": limit,
            },
            timeout=10
        )
        resp2.raise_for_status()
        events = resp2.json()

        # Events contain nested markets — extract them
        for event in events:
            for m in event.get("markets", []):
                m["_event_title"] = event.get("title", "")
                m["_event_category"] = event.get("category", "")
                all_markets.append(m)

        print(f"  [agent] Events endpoint: {len(events)} events extracted")
    except Exception as e:
        print(f"  [agent] Events endpoint error: {e}")

    # Clean and filter
    cleaned = []
    seen_ids = set()

    for m in all_markets:
        mid = m.get("id")
        if not mid or mid in seen_ids:
            continue
        seen_ids.add(mid)

        # Parse price
        raw_prices = m.get("outcomePrices", "[]")
        try:
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
            yes_price = float(prices[0]) if prices else 0.5
        except Exception:
            yes_price = 0.5

        volume = float(m.get("volume") or 0)
        question = m.get("question", "").lower()

        # Relaxed filters — only remove truly dead markets
        if volume < 1000:           # was 5000, relaxed
            continue
        if yes_price < 0.02 or yes_price > 0.98:   # was 0.05/0.95, relaxed
            continue

        # Only hard-filter truly absurd memes
        if any(kw in question for kw in HARD_MEME_FILTER):
            continue

        cleaned.append({
            "id": mid,
            "question": m.get("question", ""),
            "description": m.get("description", "")[:150],
            "yes_price": yes_price,
            "volume": volume,
            "category": m.get("_event_category", m.get("category", "")),
            "event": m.get("_event_title", ""),
        })

    # Sort by volume descending
    cleaned.sort(key=lambda x: x["volume"], reverse=True)

    print(f"  [agent] {len(cleaned)} quality markets after filtering")

    _market_cache = cleaned
    _cache_timestamp = now
    return cleaned


def claude_match_markets(signal: dict, markets: list[dict]) -> list[dict]:
    """
    Claude Haiku does semantic matching.
    We send markets in batches if there are many.
    """
    if not markets:
        return []

    # Build market index — include category hint to help Claude
    market_index = "\n".join([
        f"{i}. [{m['yes_price']:.2f}] {m['question']}"
        + (f" [{m['category']}]" if m.get('category') else "")
        for i, m in enumerate(markets[:100])  # cap at 100 for token limit
    ])

    prompt = f"""You are a prediction market analyst. Identify which markets are directly affected by this news signal.

SIGNAL:
Title: {signal['title']}
Summary: {signal.get('summary', '')}

MARKETS (index. [YES probability] question [category]):
{market_index}

Rules:
- Only select markets where this signal meaningfully changes the probability
- A signal about Bitcoin price affects crypto markets, not sports markets
- A signal about a specific team affects that team's markets
- Be selective — better to return 0-3 highly relevant markets than 10 weak ones

Return ONLY a JSON array of index numbers. Example: [2, 7]
If none are relevant return: []
No explanation. Just the array."""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1:
            return []

        indices = json.loads(raw[start:end])
        matched = [markets[i] for i in indices if isinstance(i, int) and i < len(markets)]
        return matched

    except Exception as e:
        print(f"  [agent] Matching error: {e}")
        return []


def find_markets_for_signal(signal: dict) -> list[dict]:
    """Main entry point for brain.py"""
    print(f"  [agent] Loading market universe...")
    all_markets = fetch_all_markets()

    if not all_markets:
        print(f"  [agent] No markets available")
        return []

    print(f"  [agent] Semantically matching against {len(all_markets)} markets...")
    matched = claude_match_markets(signal, all_markets)
    print(f"  [agent] {len(matched)} relevant markets found")
    return matched


if __name__ == "__main__":
    test_signals = [
        {
            "title": "Federal Reserve holds interest rates steady, signals no cuts in 2025",
            "summary": "The Fed kept rates at 5.25-5.5% and needs more evidence of inflation cooling.",
            "source": "Reuters"
        },
        {
            "title": "Mohamed Salah picks up hamstring injury, out for 3 weeks",
            "summary": "Liverpool star forward Salah ruled out of next three Premier League matches.",
            "source": "Sky Sports"
        },
        {
            "title": "Trump signs executive order on Bitcoin strategic reserve",
            "summary": "President Trump signed an EO establishing a national Bitcoin strategic reserve.",
            "source": "Reuters"
        },
        {
            "title": "Harvey Weinstein sentencing delayed by judge",
            "summary": "The judge has postponed Harvey Weinstein sentencing to next month.",
            "source": "CNN"
        },
    ]

    for signal in test_signals:
        print(f"\n{'='*60}")
        print(f"Signal: {signal['title']}")
        markets = find_markets_for_signal(signal)

        if markets:
            print(f"Matched markets:")
            for m in markets:
                print(f"  YES:{m['yes_price']:.2f} | Vol:${m['volume']:,.0f} | {m['question']}")
        else:
            print("  No relevant markets found")

    # Also print what the full universe looks like
    print(f"\n{'='*60}")
    print("Full market universe sample (top 15 by volume):")
    universe = fetch_all_markets()
    for m in universe[:15]:
        print(f"  YES:{m['yes_price']:.2f} | Vol:${m['volume']:,.0f} | [{m['category']}] {m['question']}")