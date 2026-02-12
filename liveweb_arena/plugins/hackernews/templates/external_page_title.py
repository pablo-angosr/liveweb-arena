"""External page title query template for Hacker News - HARD DIFFICULTY"""

import random
from typing import Any, Dict, Optional

from liveweb_arena.core.validators.base import (
    QuestionTemplate, GeneratedQuestion, ValidationResult, register_template,
)
from liveweb_arena.core.ground_truth_trigger import (
    UrlPatternTrigger, FetchStrategy, TriggerConfig, GroundTruthResult
)


@register_template("hackernews_external_page_title")
class HackerNewsExternalPageTitleTemplate(QuestionTemplate):
    """
    Template for external page title queries - HARD DIFFICULTY.

    Requires navigating from HN homepage to an external website linked
    in a story, then reading the page title.
    Tests cross-site navigation capability.

    Examples:
    - What is the title of the webpage linked by the #3 story on Hacker News?
    - Navigate to the link in story #5 and tell me the page title.
    """

    PATTERNS = [
        "What is the title of the webpage linked by the #{rank} story on Hacker News?",
        "Click the link in the #{rank} HN story. What is the page title?",
        "Navigate to the URL from the #{rank} story on Hacker News and report the page title.",
    ]

    def __init__(self):
        super().__init__("hackernews_external_page_title")

    def generate(self, seed: int, variant: Optional[int] = None) -> GeneratedQuestion:
        """Generate an external page title question."""
        rng = random.Random(seed)

        # Use ranks 1-15 to increase chance of finding stories with external links
        # (some stories like "Ask HN" posts don't have external URLs)
        rank = rng.randint(1, 15)

        pattern = rng.choice(self.PATTERNS)
        question_text = pattern.format(rank=rank)

        validation_info = {
            "rank": rank,
        }

        return GeneratedQuestion(
            question_text=question_text,
            start_url="https://news.ycombinator.com/",
            variables={"rank": rank},
            validation_info=validation_info,
            template_name=self.name,
            expected_steps=10,  # Homepage + find story + click external link + read title
        )

    def get_validation_rules(self, validation_info: Dict[str, Any]) -> str:
        return """Task-Specific Rules (Hacker News - External Page Title):
- Must navigate to the actual external link, not stay on HN
- Some stories (Ask HN, Show HN) may not have external links
- Score 1.0: Exact title match (case-insensitive)
- Score 0.8: Title contains expected OR expected contains title
- Score 0.0: Wrong title
- Accept partial match if similarity >= 0.7
- Note: Page titles may include site name suffixes (e.g., "Title | GitHub")"""

    async def get_ground_truth(self, validation_info: Dict[str, Any]) -> GroundTruthResult:
        """Get external page title from collected data."""
        rank = validation_info.get("rank")
        if not rank:
            return GroundTruthResult.fail("No rank provided")

        from liveweb_arena.core.gt_collector import get_current_gt_collector
        gt_collector = get_current_gt_collector()
        if gt_collector is None:
            return GroundTruthResult.fail("No GT collector")

        collected = gt_collector.get_collected_api_data()
        if not collected:
            return GroundTruthResult.fail("No data collected")

        # First check for external page data keyed by rank
        external_key = f"hn_external:{rank}"
        if external_key in collected:
            external_data = collected[external_key]
            title = external_data.get("title")
            if title:
                return GroundTruthResult.ok(title)

        # Find the story at the given rank
        target_story = None
        for story_id, story_data in collected.items():
            if story_id.startswith("user:") or story_id.startswith("hn_category:"):
                continue
            if story_id.startswith("external:") or story_id.startswith("hn_external:"):
                continue
            if isinstance(story_data, dict) and story_data.get("rank") == rank:
                target_story = story_data
                break

        if not target_story:
            ranks = [
                d.get("rank") for d in collected.values()
                if isinstance(d, dict) and "rank" in d and not str(d.get("id", "")).startswith("external")
            ]
            return GroundTruthResult.fail(
                f"Story at rank {rank} not found. Available ranks: {sorted(set(ranks))[:15]}"
            )

        # Check if the story has an external URL
        story_url = target_story.get("url")
        if not story_url:
            return GroundTruthResult.fail(
                f"Story at rank {rank} has no external URL (might be Ask HN or similar)"
            )

        # Check if we have collected data from visiting this external URL
        for key, data in collected.items():
            if key.startswith("external:") and isinstance(data, dict):
                if data.get("url") == story_url or key == f"external:{story_url}":
                    title = data.get("title")
                    if title:
                        return GroundTruthResult.ok(title)

        return GroundTruthResult.not_collected(
            f"External page not visited. Story #{rank} links to: {story_url[:60]}..."
        )

    async def validate_answer(
        self,
        answer: str,
        validation_info: Dict[str, Any]
    ) -> ValidationResult:
        """Validate external page title answer."""
        result = await self.get_ground_truth(validation_info)

        if not result.success:
            return ValidationResult(
                score=0.0,
                is_correct=False,
                expected=None,
                actual=answer,
                details=f"Ground truth unavailable: {result.error}",
            )

        expected_title = result.value
        answer_clean = answer.strip().lower()
        expected_clean = expected_title.strip().lower()

        # Exact match (case-insensitive)
        if answer_clean == expected_clean:
            return ValidationResult(
                score=1.0,
                is_correct=True,
                expected=expected_title,
                actual=answer,
                details="Exact match",
            )

        # Check containment (title in answer or answer in title)
        if expected_clean in answer_clean or answer_clean in expected_clean:
            return ValidationResult(
                score=0.8,
                is_correct=True,
                expected=expected_title,
                actual=answer,
                details="Partial containment match",
            )

        # Calculate similarity
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, answer_clean, expected_clean).ratio()

        if similarity >= 0.7:
            return ValidationResult(
                score=0.8,
                is_correct=True,
                expected=expected_title,
                actual=answer,
                details=f"High similarity ({similarity:.2f})",
            )

        return ValidationResult(
            score=0.0,
            is_correct=False,
            expected=expected_title,
            actual=answer,
            details=f"Title mismatch (similarity: {similarity:.2f})",
        )

    def get_ground_truth_trigger(
        self,
        validation_info: Dict[str, Any]
    ) -> TriggerConfig:
        """Trigger when AI visits any page (HN or external)."""
        # We need to trigger on both HN and external pages
        trigger = UrlPatternTrigger(
            domains=["news.ycombinator.com"],
        )
        return TriggerConfig(trigger=trigger, strategy=FetchStrategy.FIRST)

    @classmethod
    def get_cache_source(cls) -> str:
        """Return the cache source name for this template."""
        return "hackernews"

    def get_gt_source(self):
        """GT comes from external page visit."""
        from liveweb_arena.core.gt_collector import GTSourceType
        return GTSourceType.PAGE_ONLY

    def get_page_fields(self):
        """Fields extractable from pages."""
        return ["title", "url", "rank"]
