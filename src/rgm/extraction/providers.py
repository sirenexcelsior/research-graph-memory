from __future__ import annotations

from rgm.config import RGMConfig
from rgm.extraction.base import ExtractorProvider
from rgm.extraction.hermes_provider import HermesExtractor
from rgm.extraction.rule_based import RuleBasedResearchExtractor


def get_extractor(provider: str | None = None, *, config: RGMConfig | None = None) -> ExtractorProvider | None:
    cfg = config or RGMConfig.load()
    extraction_config = cfg.read_yaml("extraction.yaml")
    if extraction_config.get("enabled", True) is False:
        return None

    selected = provider or extraction_config.get("provider", "rule_based")
    if selected in {"none", "off", "disabled"}:
        return None
    if selected == "rule_based":
        return RuleBasedResearchExtractor(extraction_config.get("rule_based", {}))
    if selected == "hermes":
        return HermesExtractor(extraction_config.get("hermes", {}))
    raise ValueError(f"Unknown extraction provider: {selected}")

