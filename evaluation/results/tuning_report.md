# Подбор гиперпараметров механики подбора

Сетка на обучающем синтетическом мире (seed 11), проверка лучшей конфигурации на независимом мире (seed 23).

| Конфигурация | Веса | NDCG@10 (train) | P@10 | MRR |
|---|---|---|---|---|
| {'MUST_GATE_FLOOR': 0.8, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.35} | grade_heavier | 0.832 | 0.827 | 0.983 |
| {'MUST_GATE_FLOOR': 0.65, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.0} | grade_heavier | 0.832 | 0.805 | 0.967 |
| {'MUST_GATE_FLOOR': 1.0, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.35} | grade_heavier | 0.830 | 0.830 | 0.983 |
| {'MUST_GATE_FLOOR': 0.8, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.0} | grade_heavier | 0.829 | 0.830 | 0.975 |
| {'MUST_GATE_FLOOR': 1.0, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.0} | grade_heavier | 0.823 | 0.828 | 0.975 |
| {'MUST_GATE_FLOOR': 0.8, 'EVIDENCE_STRENGTH': 0.25, 'TEST_COMPETENCY_SHARE': 0.0} | grade_heavier | 0.820 | 0.823 | 0.975 |
| {'MUST_GATE_FLOOR': 0.65, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.35} | grade_heavier | 0.818 | 0.795 | 0.942 |
| {'MUST_GATE_FLOOR': 1.0, 'EVIDENCE_STRENGTH': 0.25, 'TEST_COMPETENCY_SHARE': 0.0} | grade_heavier | 0.815 | 0.833 | 0.975 |

|  | NDCG@10 train | NDCG@10 held-out | P@10 held-out | MRR held-out |
|---|---|---|---|---|
| Исходная экспертная конфигурация (v1.0) | 0.624 | 0.594 | 0.573 | 0.797 |
| Лучшая на сетке | 0.832 | 0.809 | 0.792 | 0.967 |
| Принятая в продукт (v1.2) | 0.808 | 0.786 | 0.770 | 0.956 |

Продуктовая конфигурация: `{'MUST_GATE_FLOOR': 0.8, 'EVIDENCE_STRENGTH': 0.25, 'TEST_COMPETENCY_SHARE': 0.35}`, веса balanced = `{'skills': 0.26, 'test': 0.16, 'grade': 0.22, 'specialization': 0.1, 'fsp': 0.1, 'freshness': 0.06, 'salary': 0.05, 'experience': 0.03, 'format': 0.02}`. EVIDENCE_STRENGTH оставлен 0,25 (а не 0 как на сетке): подтверждённые тестом навыки — продуктовый стимул проходить тест; цена — около 0,02 NDCG на отложенных данных.

Лучшее: `{'MUST_GATE_FLOOR': 0.8, 'EVIDENCE_STRENGTH': 0.0, 'TEST_COMPETENCY_SHARE': 0.35}`, веса `grade_heavier`. Время: 235 с.
