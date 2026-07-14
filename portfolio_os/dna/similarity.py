from __future__ import annotations

from .models import RepositoryDNA, RepositorySimilarity, SimilarityDimension


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


class SimilarityEngine:
    def compare(self, left: RepositoryDNA, right: RepositoryDNA) -> RepositorySimilarity:
        dimensions: list[SimilarityDimension] = []
        weighted_score = 0.0
        active_weight = 0.0
        for name, weight in left.weights.items():
            left_values = set(getattr(left.features, name))
            right_values = set(getattr(right.features, name))
            if not left_values and not right_values:
                continue
            score = _jaccard(left_values, right_values)
            active_weight += weight
            weighted_score += score * weight
            dimensions.append(
                SimilarityDimension(
                    name=name,
                    score=score,
                    weight=weight,
                    overlap=tuple(sorted(left_values & right_values)),
                    left_only=tuple(sorted(left_values - right_values)),
                    right_only=tuple(sorted(right_values - left_values)),
                )
            )
        score = weighted_score / active_weight if active_weight else 0.0
        classification = self._classify(score)
        reasons = self._reasons(dimensions)
        return RepositorySimilarity(
            left=left.repository,
            right=right.repository,
            score=score,
            classification=classification,
            dimensions=tuple(dimensions),
            reasons=tuple(reasons),
        )

    def rank(self, repositories: list[RepositoryDNA], minimum_score: float = 0.0) -> list[RepositorySimilarity]:
        comparisons = []
        for index, left in enumerate(repositories):
            for right in repositories[index + 1 :]:
                comparison = self.compare(left, right)
                if comparison.score >= minimum_score:
                    comparisons.append(comparison)
        return sorted(comparisons, key=lambda item: (-item.score, item.left.lower(), item.right.lower()))

    def _classify(self, score: float) -> str:
        if score >= 0.75:
            return "very-high-overlap"
        if score >= 0.55:
            return "high-overlap"
        if score >= 0.35:
            return "related"
        if score >= 0.18:
            return "weakly-related"
        return "distinct"

    def _reasons(self, dimensions: list[SimilarityDimension]) -> list[str]:
        strongest = sorted(dimensions, key=lambda item: (-(item.score * item.weight), item.name))
        reasons = []
        for dimension in strongest:
            if dimension.score <= 0 or not dimension.overlap:
                continue
            sample = ", ".join(dimension.overlap[:5])
            reasons.append(f"Shared {dimension.name}: {sample}")
            if len(reasons) == 3:
                break
        return reasons
