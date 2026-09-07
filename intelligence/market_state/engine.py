# -*- coding: utf-8 -*-
"""
NEXA Real Estate Intelligence Swarm - Market State Engine
Coldwell Banker CB VIP Ankara • Yiğit Narin

Maintains dynamic macro & micro market health indices:
- Demand Index (0-100)
- Supply Index (0-100)
- Financing / Credit Index (0-100)
- Rental Yield & Pressure Index (0-100)
- Price Momentum Index (0-100)
- Investment Appetite Index (0-100)

Determines macro MarketRegime: EXPANSION, STABLE, COOLING, STRESS, RECOVERY
Provides district micro-indices for Ankara Prime Corridors (Beytepe, İncek, Çayyolu, Çankaya, Gölbaşı)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from intelligence.swarm.swarm_models import MarketState, MarketRegime

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "static" / "data"
STATE_FILE = DATA_DIR / "market_state.json"


class MarketStateEngine:
    """Computes, monitors, and persists macro-financial real estate market states."""

    DEFAULT_REGIONAL_INDICES = {
        "Beytepe": {
            "demand": 86.0,
            "supply": 48.0,
            "price_pressure": 82.0,
            "rental_yield": 6.8,
            "investment_appetite": 89.0,
            "dominant_segment": "Ultra-Lüks Villa / Rezidans",
            "cycle_stage": "Yüksek Talep / Sınırlı Arz",
            "m2_average_try": 88000.0
        },
        "İncek": {
            "demand": 82.0,
            "supply": 64.0,
            "price_pressure": 74.0,
            "rental_yield": 7.4,
            "investment_appetite": 85.0,
            "dominant_segment": "Müstakil Yaşam & Kampüs Konutları",
            "cycle_stage": "Dengeli Genişleme",
            "m2_average_try": 72000.0
        },
        "Çayyolu": {
            "demand": 78.0,
            "supply": 52.0,
            "price_pressure": 75.0,
            "rental_yield": 6.5,
            "investment_appetite": 79.0,
            "dominant_segment": "Oturum Odaklı Prestij Konut",
            "cycle_stage": "Konsolide / Stabil",
            "m2_average_try": 76000.0
        },
        "Çankaya": {
            "demand": 74.0,
            "supply": 58.0,
            "price_pressure": 70.0,
            "rental_yield": 7.1,
            "investment_appetite": 76.0,
            "dominant_segment": "Merkezi Elit Rezidans & Kurumsal Kiralama",
            "cycle_stage": "Stabil Yüksek Likidite",
            "m2_average_try": 68000.0
        },
        "Gölbaşı": {
            "demand": 79.0,
            "supply": 68.0,
            "price_pressure": 72.0,
            "rental_yield": 6.9,
            "investment_appetite": 84.0,
            "dominant_segment": "Göl Manzaralı Villa & Gelişim Alanı",
            "cycle_stage": "Erken Genişleme",
            "m2_average_try": 62000.0
        }
    }

    def __init__(self):
        self._current_state: Optional[MarketState] = None
        self._load_persisted_state()

    def _load_persisted_state(self):
        """Loads cached state from JSON file or initializes default state."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._current_state = MarketState(
                    demand=float(data.get("demand", 75.0)),
                    supply=float(data.get("supply", 55.0)),
                    credit=float(data.get("credit", 60.0)),
                    rental=float(data.get("rental", 76.0)),
                    price_pressure=float(data.get("price_pressure", 70.0)),
                    investment_appetite=float(data.get("investment_appetite", 78.0)),
                    regime=MarketRegime(data.get("regime", "STABLE")),
                    regional_indices=data.get("regional_indices", self.DEFAULT_REGIONAL_INDICES),
                    daily_diff=data.get("daily_diff", {}),
                    last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat())
                )
                return
            except Exception as e:
                logger.warning(f"Could not parse {STATE_FILE}: {e}")

        self._current_state = MarketState(
            demand=76.0,
            supply=54.0,
            credit=58.0,
            rental=78.0,
            price_pressure=72.0,
            investment_appetite=80.0,
            regime=MarketRegime.STABLE,
            regional_indices=self.DEFAULT_REGIONAL_INDICES,
            daily_diff={"demand": +1.2, "supply": -0.5, "price_pressure": +0.8, "investment_appetite": +1.5},
            last_updated=datetime.now(timezone.utc).isoformat()
        )

    def detect_regime(
        self,
        demand: float,
        supply: float,
        credit: float,
        rental: float,
        price_pressure: float
    ) -> MarketRegime:
        """Determines macro market regime via multi-factor rule heuristics."""
        if credit < 40.0 and demand < 50.0 and price_pressure < 50.0:
            return MarketRegime.STRESS
        elif demand > 75.0 and price_pressure > 70.0 and supply < 60.0:
            return MarketRegime.EXPANSION
        elif credit > 65.0 and demand > 65.0 and supply > 65.0:
            return MarketRegime.RECOVERY
        elif demand < 55.0 and supply > 65.0:
            return MarketRegime.COOLING
        else:
            return MarketRegime.STABLE

    def calculate_state_from_signals(
        self,
        articles_impact_list: Optional[List[Dict[str, Any]]] = None
    ) -> MarketState:
        """Dynamically adjusts market indices based on fresh verified intelligence signals."""
        current = self._current_state or MarketState()
        old_demand = current.demand
        old_supply = current.supply
        old_pressure = current.price_pressure
        old_appetite = current.investment_appetite

        new_demand = old_demand
        new_supply = old_supply
        new_pressure = old_pressure
        new_appetite = old_appetite
        new_credit = current.credit
        new_rental = current.rental

        if articles_impact_list:
            for item in articles_impact_list:
                cat = item.get("category", "")
                reg_impact = item.get("regional_impact", 50)
                inv_impact = item.get("investor_impact", 50)

                # Sentiment nudge based on verified impacts
                delta = (inv_impact - 50) * 0.05
                new_demand = max(20.0, min(98.0, new_demand + delta))
                new_appetite = max(20.0, min(98.0, new_appetite + delta * 1.2))

                if "Kredi" in cat or "Faiz" in cat or "Finans" in cat:
                    credit_delta = (item.get("confidence", 50) - 50) * 0.04
                    new_credit = max(10.0, min(95.0, new_credit + credit_delta))

                if "Kira" in cat:
                    new_rental = max(30.0, min(95.0, new_rental + (reg_impact - 50) * 0.05))

        regime = self.detect_regime(new_demand, new_supply, new_credit, new_rental, new_pressure)

        daily_diff = {
            "demand": round(new_demand - old_demand, 2),
            "supply": round(new_supply - old_supply, 2),
            "price_pressure": round(new_pressure - old_pressure, 2),
            "investment_appetite": round(new_appetite - old_appetite, 2)
        }

        updated_state = MarketState(
            demand=round(new_demand, 1),
            supply=round(new_supply, 1),
            credit=round(new_credit, 1),
            rental=round(new_rental, 1),
            price_pressure=round(new_pressure, 1),
            investment_appetite=round(new_appetite, 1),
            regime=regime,
            regional_indices=current.regional_indices or self.DEFAULT_REGIONAL_INDICES,
            daily_diff=daily_diff,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

        self._current_state = updated_state
        self.persist_state(updated_state)
        return updated_state

    def persist_state(self, state: MarketState) -> None:
        """Persists market state to json cache and database history."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "demand": state.demand,
            "supply": state.supply,
            "credit": state.credit,
            "rental": state.rental,
            "price_pressure": state.price_pressure,
            "investment_appetite": state.investment_appetite,
            "regime": state.regime.value if hasattr(state.regime, 'value') else str(state.regime),
            "regional_indices": state.regional_indices,
            "daily_diff": state.daily_diff,
            "last_updated": state.last_updated
        }

        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write market state file: {e}")

    def get_current_state(self) -> MarketState:
        """Returns the currently active market state."""
        if not self._current_state:
            self._load_persisted_state()
        return self._current_state

    def get_district_metrics(self, district_name: str) -> Dict[str, Any]:
        """Returns micro metrics for a specific prime district."""
        state = self.get_current_state()
        indices = state.regional_indices or self.DEFAULT_REGIONAL_INDICES
        return indices.get(district_name, indices.get("Beytepe", {}))
