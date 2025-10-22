"""Pruebas para el módulo de aprendizaje adaptativo."""

from __future__ import annotations

from horizonte.core.adaptive_learning import AdaptiveTrainer


def test_adaptive_trainer_limita_buffer(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    trainer = AdaptiveTrainer(cache_path=cache_path, buffer_size=500)

    for idx in range(600):
        trainer.log_inference(
            query=f"consulta-{idx}",
            response_hash=f"hash-{idx}",
            flags=[],
            response_time_ms=12.5,
            allowed=True,
        )

    assert len(trainer.buffer) == 500


def test_update_model_feedback_ajusta_sensibilidad(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    trainer = AdaptiveTrainer(cache_path=cache_path, buffer_size=10)

    baseline = trainer.update_model_feedback()["posible_sesgo"]
    for _ in range(3):
        trainer.update_model_feedback(["posible_sesgo"])

    updated = trainer.update_model_feedback()
    assert updated["posible_sesgo"] > baseline
