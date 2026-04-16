"""
ai_analyst.py — GPT-5-mini powered trade analysis and signal validation.

Uses Replit AI Integrations (no API key required from user).
Analyzes every trade setup before execution and filters weak signals.
"""

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass

from config import (
    AI_BASE_URL, AI_API_KEY,
    AI_MODEL, AI_CONFIDENCE_THRESHOLD, AI_MAX_TOKENS,
    AI_REGIME_MULTIPLIERS,
)

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysis:
    confidence: int          # 0–100
    approved: bool           # True = AI approves the trade
    reasoning: str           # Short explanation
    risk_warnings: list[str] # List of risk flags
    market_regime: str       # 'trending', 'ranging', 'volatile', 'uncertain'
    enhanced_score: float    # AI-boosted setup score


def _build_client():
    """Build OpenAI client pointing at Replit AI proxy."""
    if not AI_BASE_URL or not AI_API_KEY:
        raise RuntimeError(
            "AI_INTEGRATIONS_OPENAI_BASE_URL or AI_INTEGRATIONS_OPENAI_API_KEY not set"
        )
    from openai import OpenAI
    return OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)


def _regime_multiplier(regime: str) -> float:
    return AI_REGIME_MULTIPLIERS.get(regime, 1.0)


def _build_system_prompt() -> str:
    threshold = AI_CONFIDENCE_THRESHOLD
    return f"""You are an elite Forex and Crypto trading analyst with 20+ years of experience.
You specialize in Support & Resistance strategies, price action, and risk management.
Your job is to evaluate trade setups and provide an honest, rigorous assessment.

You must respond ONLY with a valid JSON object (no markdown, no extra text) with this exact structure:
{{
  "confidence": <integer 0-100>,
  "approved": <boolean>,
  "reasoning": "<concise 2-3 sentence analysis>",
  "risk_warnings": ["<warning1>", "<warning2>"],
  "market_regime": "<trending|ranging|volatile|uncertain>",
  "enhanced_score": <float>
}}

Guidelines:
- confidence >= 70: Strong setup, approve
- confidence 50-69: Marginal, only approve if risk is very controlled
- confidence < 50: Reject — do not trade this setup
- approved must be true only if confidence >= {threshold}
- risk_warnings: identify any red flags (news risk, thin liquidity, S/R zone quality, etc.)
- market_regime: assess based on the EMA relationship and ATR data
- enhanced_score: original_score * (confidence / 100) * regime_multiplier
  where regime_multiplier is 1.2 for trending, 1.0 for ranging, 0.7 for volatile, 0.5 for uncertain
"""


def _build_user_prompt(setup: dict) -> str:
    now_utc = datetime.now(timezone.utc)
    symbol = setup["symbol"]
    direction = setup["direction"]
    current_price = setup["current_price"]
    zone_price = setup["zone_price"]
    atr = setup.get("atr", 0.0)
    pattern = setup.get("pattern", "none")
    rsi = setup.get("rsi")
    score = setup.get("score", 0.0)
    balance = setup.get("balance", 0.0)
    zone_kind = "support" if direction == "BUY" else "resistance"

    zone_distance_pct = abs(current_price - zone_price) / zone_price * 100

    rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
    atr_str = f"{atr:.6f}" if atr else "N/A"

    return f"""Evaluate this trade setup:

TIME: {now_utc.strftime('%Y-%m-%d %H:%M UTC')} (Day of week: {now_utc.strftime('%A')})
SYMBOL: {symbol}
DIRECTION: {direction}
CURRENT PRICE: {current_price:.5f}
{zone_kind.upper()} ZONE: {zone_price:.5f} ({zone_distance_pct:.3f}% from price)

TECHNICAL SIGNALS:
- 15M Trend (EMA50/200): Aligned with {direction}
- Candlestick Pattern (1M): {pattern.replace('_', ' ').upper() if pattern else 'NONE'}
- RSI (1M): {rsi_str} {'(oversold — buy signal)' if rsi is not None and rsi < 30 else '(overbought — sell signal)' if rsi is not None and rsi > 70 else ''}
- ATR (volatility): {atr_str}
- Zone Touch Score: {score:.1f}

ACCOUNT CONTEXT:
- Account Balance: ${balance:.2f} USD
- Risk per trade: 1% (${balance * 0.01:.2f})

Provide your analysis as JSON."""


def analyze_setup(setup: dict) -> AIAnalysis:
    """
    Run AI analysis on a trade setup.
    Returns AIAnalysis with confidence score, approval, and reasoning.
    Falls back gracefully if AI is unavailable.
    """
    default = AIAnalysis(
        confidence=70,
        approved=True,
        reasoning="AI analysis unavailable — proceeding with technical confirmation only.",
        risk_warnings=[],
        market_regime="uncertain",
        enhanced_score=setup.get("score", 1.0),
    )

    if not AI_BASE_URL or not AI_API_KEY:
        logger.warning("AI integration not configured — skipping AI analysis")
        return default

    try:
        client = _build_client()
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": _build_user_prompt(setup)},
            ],
            max_completion_tokens=AI_MAX_TOKENS,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code blocks if model wraps in them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)

        confidence = int(data.get("confidence", 70))
        approved = bool(data.get("approved", confidence >= AI_CONFIDENCE_THRESHOLD))
        reasoning = str(data.get("reasoning", ""))
        risk_warnings = list(data.get("risk_warnings", []))
        market_regime = str(data.get("market_regime", "uncertain"))
        enhanced_score = float(data.get("enhanced_score", setup.get("score", 1.0)))

        logger.info(
            f"AI analysis for {setup['symbol']} {setup['direction']}: "
            f"confidence={confidence}, approved={approved}, regime={market_regime}"
        )
        if reasoning:
            logger.info(f"AI reasoning: {reasoning}")
        if risk_warnings:
            logger.warning(f"AI risk warnings: {risk_warnings}")

        return AIAnalysis(
            confidence=confidence,
            approved=approved,
            reasoning=reasoning,
            risk_warnings=risk_warnings,
            market_regime=market_regime,
            enhanced_score=enhanced_score,
        )

    except json.JSONDecodeError as e:
        logger.error(f"AI returned invalid JSON: {e}")
        return default
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return default


def format_ai_alert_section(analysis: AIAnalysis) -> str:
    """Format AI analysis for Telegram alert."""
    bar_filled = round(analysis.confidence / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    approval_icon = "✅" if analysis.approved else "❌"

    lines = [
        f"",
        f"<b>🤖 AI Analysis</b>",
        f"<b>Confidence:</b> {analysis.confidence}% [{bar}]",
        f"<b>Decision:</b> {approval_icon} {'APPROVED' if analysis.approved else 'REJECTED'}",
        f"<b>Regime:</b> {analysis.market_regime.title()}",
        f"<b>Reasoning:</b> {analysis.reasoning}",
    ]
    if analysis.risk_warnings:
        warnings_str = " | ".join(analysis.risk_warnings)
        lines.append(f"<b>⚠️ Risks:</b> {warnings_str}")

    return "\n".join(lines)
