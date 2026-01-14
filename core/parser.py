"""Answer parser for extracting structured answers from agent output"""

import re
from typing import Any, Dict, Optional


class AnswerParser:
    """
    Parser for extracting answers from agent's final output.

    Supports two formats:
    1. JSON (primary): {"answers": {"answer1": "...", ...}}
    2. Fallback: <answerN>...</answerN> tags
    """

    def parse_answers(
        self, response: Any, num_answers: int
    ) -> Dict[str, Optional[str]]:
        """
        Parse answers from agent response.

        Args:
            response: The final answer from agent (dict, str, or None)
            num_answers: Expected number of answers (1-4)

        Returns:
            Dict with keys "answer1"..."answerN", values are answer strings or None
        """
        # Initialize result with None for all expected answers
        result = {f"answer{i+1}": None for i in range(num_answers)}

        if response is None:
            return result

        # Try JSON-first parsing
        answers = self._parse_json_answers(response)

        # If JSON parsing fails, try tag-based fallback
        if not answers:
            if isinstance(response, str):
                answers = self._parse_tag_answers(response)
            elif isinstance(response, dict):
                # Try to extract from nested structure
                raw = response.get("final_raw", "")
                if raw:
                    answers = self._parse_tag_answers(raw)

        # Merge parsed answers into result
        for key, value in answers.items():
            if key in result:
                result[key] = value

        return result

    def _parse_json_answers(self, response: Any) -> Dict[str, str]:
        """
        Parse answers from JSON format.

        Accepts:
        - {"answers": {"answer1": "...", ...}}
        - {"answers": [{"id": 1, "value": "..."}, ...]}
        - Direct dict with answer keys
        """
        answers = {}

        if isinstance(response, dict):
            # Check for "answers" key
            if "answers" in response:
                answers_data = response["answers"]

                if isinstance(answers_data, dict):
                    # Format: {"answers": {"answer1": "...", ...}}
                    for key, value in answers_data.items():
                        if key.startswith("answer") and value is not None:
                            answers[key] = str(value)

                elif isinstance(answers_data, list):
                    # Format: {"answers": [{"id": 1, "value": "..."}, ...]}
                    for item in answers_data:
                        if isinstance(item, dict):
                            idx = item.get("id")
                            value = item.get("value")
                            if idx is not None and value is not None:
                                answers[f"answer{idx}"] = str(value)

            else:
                # Check for direct answer keys in response
                for key, value in response.items():
                    if key.startswith("answer") and value is not None:
                        answers[key] = str(value)

        return answers

    def _parse_tag_answers(self, text: str) -> Dict[str, str]:
        """
        Parse answers from <answerN>...</answerN> tags.

        This is the fallback format when JSON parsing fails.
        """
        answers = {}

        # Pattern: <answerN>content</answerN>
        pattern = r"<answer(\d+)>(.*?)</answer\1>"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for num, content in matches:
            answers[f"answer{num}"] = content.strip()

        return answers

    def get_output_format(self, response: Any) -> str:
        """
        Determine which output format was used.

        Returns:
            "json" if JSON format was successfully parsed
            "fallback_tags" if tag format was used
            "none" if no valid format found
        """
        if response is None:
            return "none"

        # Check JSON format
        json_answers = self._parse_json_answers(response)
        if json_answers:
            return "json"

        # Check tag format
        if isinstance(response, str):
            tag_answers = self._parse_tag_answers(response)
            if tag_answers:
                return "fallback_tags"
        elif isinstance(response, dict):
            raw = response.get("final_raw", "")
            if raw:
                tag_answers = self._parse_tag_answers(raw)
                if tag_answers:
                    return "fallback_tags"

        return "none"
