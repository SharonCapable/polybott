# main.py — updated loop

import time
from modules.agent_scanner import find_markets_for_signal  # replaces scanner
from modules.signals import get_all_signals
from modules.brain import analyze_signal
from modules.risk import calculate_bet_size
from modules.logger import log_signal, print_summary

BANKROLL = 5.00
LOOP_INTERVAL = 300
PAPER_TRADE = True

def run():
    print("🤖 Polybot starting — agent mode" if not PAPER_TRADE else "🤖 Polybot starting — paper trade + agent mode")
    print(f"   Bankroll: ${BANKROLL} | Checking every {LOOP_INTERVAL}s\n")

    while True:
        try:
            print(f"[loop] Fetching signals...")
            signals = get_all_signals()
            print(f"[loop] {len(signals)} signals incoming\n")

            for signal in signals:
                print(f"\n[loop] Processing: {signal['title'][:70]}...")

                # Agent hunts for relevant markets per signal
                markets = find_markets_for_signal(signal)

                if not markets:
                    print(f"  [agent] No relevant markets found, skipping")
                    continue

                # Brain analyzes signal against the agent's shortlist
                decision = analyze_signal(signal, markets)

                if decision and decision.get("trade"):
                    bet = calculate_bet_size(
                        BANKROLL,
                        decision.get("confidence", 0),
                        decision.get("edge", 0)
                    )

                    if bet > 0:
                        log_signal(signal, decision, bet, BANKROLL)

                        if PAPER_TRADE:
                            print(f"\n  📋 PAPER TRADE:")
                            print(f"     {decision['side']} ${bet:.4f} on: {decision['market_question']}")
                            print(f"     Edge: {decision['edge']} | Conf: {decision['confidence']}")
                            print(f"     Why: {decision['reasoning']}\n")

            print_summary()

        except Exception as e:
            print(f"[loop] Error: {e}")

        print(f"\n[loop] Sleeping {LOOP_INTERVAL}s...")
        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    run()