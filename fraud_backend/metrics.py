"""Compteurs de monitoring du scoring temps réel (thread-safe, cumulatifs).

Exposés via ``GET /metrics`` — à la différence de ``/api/dashboard`` (fenêtre
glissante de 6000 tx), ces compteurs sont cumulatifs depuis le démarrage et
servent la supervision : débit, taux d'alerte, latence, erreurs, drift de score.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = datetime.now(timezone.utc)
        self.scored_total = 0
        self.error_total = 0
        self.alert_total = 0            # fraud_predicted == 1
        self._score_sum = 0.0
        self._latency_sum_ms = 0.0
        self.last_scored_at: str | None = None
        # Histogramme des scores en 10 bacs (drift de distribution)
        self.score_bins = [0] * 10

    def observe(self, result: dict, latency_ms: float) -> None:
        with self._lock:
            self.scored_total += 1
            self.alert_total += 1 if result.get("fraud_predicted") == 1 else 0
            self._latency_sum_ms += latency_ms
            score = result.get("fraud_score")
            if isinstance(score, (int, float)):
                self._score_sum += score
                idx = min(9, max(0, int(score * 10)))
                self.score_bins[idx] += 1
            self.last_scored_at = datetime.now(timezone.utc).isoformat()

    def observe_error(self) -> None:
        with self._lock:
            self.error_total += 1

    def snapshot(self) -> dict:
        with self._lock:
            n = self.scored_total
            uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            return {
                "uptime_seconds": round(uptime, 1),
                "scored_total": n,
                "error_total": self.error_total,
                "alert_total": self.alert_total,
                "alert_rate_pct": round(self.alert_total / n * 100, 2) if n else 0.0,
                "error_rate_pct": round(
                    self.error_total / (n + self.error_total) * 100, 2
                ) if (n + self.error_total) else 0.0,
                "throughput_per_min": round(n / uptime * 60, 2) if uptime > 0 else 0.0,
                "avg_score": round(self._score_sum / n, 4) if n else 0.0,
                "avg_latency_ms": round(self._latency_sum_ms / n, 2) if n else 0.0,
                "score_distribution": [
                    {"bucket": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "count": c}
                    for i, c in enumerate(self.score_bins)
                ],
                "last_scored_at": self.last_scored_at,
            }
