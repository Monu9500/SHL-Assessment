from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessedAssessment(BaseModel):
    entity_id: str
    name: str
    url: str
    description: str = ""
    duration: str = ""
    languages: list[str] = Field(default_factory=list)
    job_levels: list[str] = Field(default_factory=list)
    keys: list[str] = Field(default_factory=list)
    remote: str = ""
    adaptive: str = ""
    searchable_text: str = ""
    test_type: str = ""

    def format_for_prompt(self, index_one_based: int) -> str:
        langs = ", ".join(self.languages[:12])
        extras = ""
        if len(self.languages) > 12:
            extras = f" (+{len(self.languages) - 12} more)"
        levels = ", ".join(self.job_levels[:8])
        keys = ", ".join(self.keys)
        return (
            f"[#{index_one_based}] entity_id={self.entity_id}\n"
            f"    name={self.name}\n"
            f"    url={self.url}\n"
            f"    test_type={self.test_type}\n"
            f"    keys={keys}\n"
            f"    duration={self.duration or '-'}\n"
            f"    languages={langs}{extras}\n"
            f"    job_levels={levels}\n"
            f"    remote={self.remote} adaptive={self.adaptive}\n"
            f"    description={self.description[:900]}"
        )
