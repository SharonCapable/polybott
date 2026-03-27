import feedparser
import requests
import os
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Feeds tuned to what Polymarket actually has markets for
RSS_FEEDS = [
    # US Politics & crypto — Polymarket's bread and butter
    ("https://feeds.npr.org/1001/rss.xml", "NPR News"),
    ("https://rss.politico.com/politics-news.xml", "Politico"),
    ("https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "WSJ Markets"),
    # Crypto
    ("https://cointelegraph.com/rss", "CoinTelegraph"),
    ("https://decrypt.co/feed", "Decrypt"),
    # Sports — EPL + NBA
    ("https://www.espn.com/espn/rss/nba/news", "ESPN NBA"),
    ("https://feeds.skysports.com/skysports/football/news", "Sky Sports Football"),
]

def get_rss_headlines(max_per_feed=5):
    headlines = []
    for url, source_name in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                headlines.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "source": source_name,
                    "link": entry.get("link", ""),
                })
        except Exception as e:
            print(f"[signals] RSS error for {source_name}: {e}")
    return headlines


def get_news_api_headlines(max=15):
    if not NEWS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "apiKey": NEWS_API_KEY,
                "language": "en",
                "pageSize": max,
                # Top headlines most likely to move prediction markets
                "category": "general",
                "country": "us",
            },
            timeout=10
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {
                "title": a.get("title", ""),
                "summary": a.get("description", "")[:300],
                "source": a.get("source", {}).get("name", "NewsAPI"),
                "link": a.get("url", ""),
            }
            for a in articles if a.get("title")
        ]
    except Exception as e:
        print(f"[signals] NewsAPI error: {e}")
        return []


def get_all_signals():
    signals = []
    signals += get_rss_headlines()
    signals += get_news_api_headlines()

    seen = set()
    unique = []
    for s in signals:
        if s["title"] not in seen and s["title"]:
            seen.add(s["title"])
            unique.append(s)

    return unique


if __name__ == "__main__":
    signals = get_all_signals()
    print(f"Got {len(signals)} signals\n")
    for s in signals[:10]:
        print(f"  [{s['source']}] {s['title']}")