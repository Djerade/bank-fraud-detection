"""Thread de fond : consomme le topic brut, score chaque transaction, remplit le Store."""
from __future__ import annotations

import json
import sys
import threading
import time

from kafka import KafkaConsumer

from .metrics import Metrics
from .scoring import Scorer
from .store import Store, normalize


class ScoringConsumer:
    """Boucle Kafka exécutée dans un thread démon, avec reconnexion automatique."""

    def __init__(
        self,
        scorer: Scorer,
        store: Store,
        metrics: Metrics,
        *,
        bootstrap: str,
        topic_in: str,
        group_id: str = "fraud-backend",
    ) -> None:
        self._scorer = scorer
        self._store = store
        self._metrics = metrics
        self._bootstrap = [h.strip() for h in bootstrap.split(",") if h.strip()]
        self._topic_in = topic_in
        self._group_id = group_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="scoring-consumer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                consumer = KafkaConsumer(
                    self._topic_in,
                    bootstrap_servers=self._bootstrap,
                    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                    group_id=self._group_id,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    consumer_timeout_ms=1000,
                )
                print(
                    f"[fraud-backend] consume {self._topic_in!r} @ {self._bootstrap}",
                    file=sys.stderr,
                )
                while not self._stop.is_set():
                    for msg in consumer:
                        if self._stop.is_set():
                            break
                        row = msg.value
                        if not isinstance(row, dict):
                            continue
                        try:
                            t0 = time.perf_counter()
                            result = self._scorer.score(row)
                            latency_ms = (time.perf_counter() - t0) * 1000
                            self._metrics.observe(result, latency_ms)
                            enriched = {**row, **result, "_scored_at": time.time()}
                            tx = normalize(enriched)
                            if tx:
                                self._store.append(tx)
                        except Exception as e:  # noqa: BLE001
                            self._metrics.observe_error()
                            print(f"[fraud-backend] erreur message : {e}", file=sys.stderr)
                consumer.close()
            except Exception as e:  # noqa: BLE001
                if self._stop.is_set():
                    break
                print(f"[fraud-backend] Kafka indisponible ({e}), retry 3s…", file=sys.stderr)
                time.sleep(3)
