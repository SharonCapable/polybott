import os
import json
import anthropic
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Clients
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 2026 Model Settings
FILTER_MODEL = "gemini-2.5-flash"
ANALYSIS_MODEL = "claude-sonnet-4-6" 

def gemini_filter(signal: dict, markets: list) -> bool:
    """
    Cheap fast check: is this signal relevant to any open market?
    """
    market_titles = "\n".join([f"- {m['question']}" for m in markets[:20]])
    prompt = f"""You are a prediction market analyst. Given this news signal and list of open markets, answer only YES or NO.

Signal: {signal['title']}
{signal.get('summary', '')}

Open markets:
{market_titles}

Could this signal meaningfully affect the probability of ANY of these markets? Answer only YES or NO."""

    try:
        # New SDK syntax
        response = gemini_client.models.generate_content(
            model=FILTER_MODEL,
            contents=prompt
        )
        answer = response.text.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        print(f"[brain] Gemini error: {e}")
        return False

def claude_analyze(signal: dict, markets: list) -> dict | None:
    market_details = "\n".join([
        f"- ID: {m['id']} | Q: {m['question']} | YES price: {m['yes_price']}"
        for m in markets[:15]
    ])

    prompt = f"""You are an expert prediction market trader. Analyze this signal and decide whether to trade.

SIGNAL:
Title: {signal['title']}
Summary: {signal.get('summary', 'N/A')}

OPEN MARKETS (question | current YES probability):
{market_details}

Respond ONLY with valid JSON, no markdown, no explanation, nothing else:
{{
  "trade": true or false,
  "market_id": "id or null",
  "market_question": "question or null",
  "side": "YES or NO or null",
  "current_price": 0.0,
  "estimated_true_prob": 0.0,
  "edge": 0.0,
  "confidence": 0.0,
  "reasoning": "brief explanation"
}}"""

    try:
        response = anthropic_client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        if not raw:
            print(f"  [brain] Claude returned empty response")
            return None

        # Strip markdown if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0].strip()

        # Find JSON object if there's surrounding text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            print(f"  [brain] No JSON found in response: {raw[:100]}")
            return None

        raw = raw[start:end]
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [brain] JSON parse error: {e} | Raw: {raw[:200]}")
        return None
    except Exception as e:
        print(f"  [brain] Claude error: {e}")
        return None

def analyze_signal(signal: dict, markets: list) -> dict | None:
    """Full pipeline: Gemini filter → Claude analysis."""
    print(f"  [brain] Checking: {signal['title'][:60]}...")

    relevant = gemini_filter(signal, markets)
    if not relevant:
        print(f"  [brain] Gemini: not relevant, discarding")
        return None

    print(f"  [brain] Gemini: relevant! Sending to Claude...")
    decision = claude_analyze(signal, markets)
    
    if decision:
        reason = decision.get("reasoning", "No specific reason")
        conf = decision.get("confidence", 0)
        edge = decision.get("edge", 0)
        
        if decision.get("trade"):
            print(f"  [brain] Claude: ✅ TRADE! {decision['side']} on '{decision['market_question'][:40]}...'")
            print(f"          (Conf: {conf}, Edge: {edge})")
        else:
            print(f"  [brain] Claude: ❌ Skip — {reason}")
            print(f"          (Conf: {conf}, Edge: {edge})")
    else:
        print(f"  [brain] Claude: ⚠️ No decision returned.")

    return decision
