import json
import os
from datetime import datetime

LOG_FILE = "trades_log.json"

def log_signal(signal: dict, decision: dict, bet_size: float, bankroll: float):
    """Log a trade decision (whether executed or not)."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "signal": signal["title"],
        "source": signal.get("source", ""),
        "trade": decision.get("trade", False),
        "market": decision.get("market_question"),
        "side": decision.get("side"),
        "confidence": decision.get("confidence"),
        "edge": decision.get("edge"),
        "bet_size": bet_size,
        "bankroll": bankroll,
        "reasoning": decision.get("reasoning"),
    }

    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return entry


def print_summary():
    """Print a quick P&L summary from the log."""
    if not os.path.exists(LOG_FILE):
        print("No trades logged yet.")
        return

    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    trades = [l for l in logs if l["trade"]]
    print(f"\n{'='*40}")
    print(f"  Total signals analyzed: {len(logs)}")
    print(f"  Trade signals generated: {len(trades)}")
    print(f"  Last 5 trade signals:")
    for t in trades[-5:]:
        print(f"    [{t['timestamp'][:16]}] {t['side']} | conf: {t['confidence']} | bet: ${t['bet_size']} | {t['market'][:40]}")
    print(f"{'='*40}\n")