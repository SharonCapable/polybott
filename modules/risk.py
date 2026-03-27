def calculate_bet_size(bankroll: float, confidence: float, edge: float, max_risk_pct: float = 0.05) -> float:
    """
    Kelly-inspired bet sizing. Never risk more than max_risk_pct of bankroll per trade.
    confidence: 0.0 to 1.0 (Claude's confidence score)
    edge: estimated_true_prob - current_price
    """
    if confidence < 0.5 or edge < 0.02:
        return 0.0  # not enough edge, skip

    # Simplified Kelly: bet = edge * confidence * bankroll, capped at max_risk_pct
    kelly_bet = edge * confidence * bankroll
    max_bet = bankroll * max_risk_pct

    bet = min(kelly_bet, max_bet)
    return round(bet, 4)


if __name__ == "__main__":
    # Test it
    bankroll = 5.00
    print(f"Bankroll: ${bankroll}")
    print(f"High confidence trade (0.8 conf, 0.12 edge): ${calculate_bet_size(bankroll, 0.8, 0.12)}")
    print(f"Low confidence trade (0.55 conf, 0.06 edge): ${calculate_bet_size(bankroll, 0.55, 0.06)}")
    print(f"Weak signal (0.5 conf, 0.03 edge): ${calculate_bet_size(bankroll, 0.5, 0.03)}")