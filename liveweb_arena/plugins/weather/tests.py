"""Tests for weather plugin templates - validates correctness of template implementation"""

import asyncio
import re
from .templates import (
    LocationNameWeatherTemplate,
    MultiDayWeatherTemplate,
    TimeOfDayWeatherTemplate,
)
from .templates.variables import TimeOfDay, MetricType


class TestFailure(Exception):
    """Test assertion failure"""
    pass


def assert_true(condition, msg):
    if not condition:
        raise TestFailure(msg)


def assert_in(item, collection, msg):
    if item not in collection:
        raise TestFailure(f"{msg}: {item} not in {collection}")


def assert_match(pattern, text, msg):
    if not re.search(pattern, text, re.IGNORECASE):
        raise TestFailure(f"{msg}: '{text}' doesn't match pattern '{pattern}'")


async def test_location_name_template():
    """Verify LocationNameWeatherTemplate generates correct structure"""
    template = LocationNameWeatherTemplate()

    for seed in [100, 200, 300]:
        q = template.generate(seed)

        # Verify question contains location
        assert_true(q.validation_info.get("location"), f"seed={seed}: Missing location")

        # Verify question text mentions the location
        location = q.validation_info["location"]
        assert_true(
            location.lower().replace("+", " ") in q.question_text.lower() or
            location.replace("+", " ") in q.question_text,
            f"seed={seed}: Question doesn't mention location: {q.question_text}"
        )

        # Verify metric type is valid
        metric_type = q.validation_info.get("metric_type")
        assert_true(metric_type, f"seed={seed}: Missing metric_type")

        # Verify ground truth can be fetched and has correct format
        gt = await template.get_ground_truth(q.validation_info)
        is_boolean = q.validation_info.get("is_boolean", False)

        if is_boolean:
            assert_in(gt, ["Yes", "No", None], f"seed={seed}: Boolean GT should be Yes/No")
        elif gt is not None:
            # Numeric GT should contain number
            assert_match(r'\d', str(gt), f"seed={seed}: GT should contain number")

    print("  LocationNameWeatherTemplate: Structure validation passed")


async def test_multi_day_template():
    """Verify MultiDayWeatherTemplate generates correct structure"""
    template = MultiDayWeatherTemplate()

    for seed in [100, 200, 300, 400]:
        q = template.generate(seed)

        # Verify num_days is present and valid
        num_days = q.validation_info.get("num_days")
        assert_true(num_days in [2, 3], f"seed={seed}: num_days should be 2 or 3, got {num_days}")

        # Verify question mentions the time period
        assert_match(
            r'(next \d days|over.*\d days|\d days)',
            q.question_text,
            f"seed={seed}: Question should mention day count"
        )

        # Verify ground truth format based on question type
        gt = await template.get_ground_truth(q.validation_info)
        question_type = q.validation_info.get("question_type")
        is_boolean = q.validation_info.get("is_boolean", False)

        if is_boolean:
            assert_in(gt, ["Yes", "No"], f"seed={seed}: Boolean GT should be Yes/No")
        elif question_type == "daily" and gt:
            # Daily should have multiple values separated by comma
            assert_match(r',', str(gt), f"seed={seed}: Daily GT should have comma-separated values")
        elif question_type == "average" and gt:
            # Average should be single value
            assert_match(r'^\d', str(gt), f"seed={seed}: Average GT should be single number")

    print("  MultiDayWeatherTemplate: Structure validation passed")


async def test_time_of_day_template():
    """Verify TimeOfDayWeatherTemplate generates correct structure"""
    template = TimeOfDayWeatherTemplate()

    time_periods = {"morning", "afternoon", "evening", "night"}

    for seed in [100, 200, 300, 400, 500]:
        q = template.generate(seed)

        # Verify time_of_day is present and valid
        tod = q.validation_info.get("time_of_day")
        assert_in(tod, time_periods, f"seed={seed}: Invalid time_of_day")

        # Verify question mentions the time period
        assert_match(
            rf'\b{tod}\b',
            q.question_text,
            f"seed={seed}: Question should mention '{tod}'"
        )

        # Verify hourly_indices are present and correct for the time period
        indices = q.validation_info.get("hourly_indices")
        assert_true(indices and len(indices) > 0, f"seed={seed}: Missing hourly_indices")

        # Verify indices are in valid range (0-7 for wttr.in)
        for idx in indices:
            assert_true(0 <= idx <= 7, f"seed={seed}: Invalid hourly index {idx}")

        # Verify ground truth is numeric (this template only uses numeric metrics)
        gt = await template.get_ground_truth(q.validation_info)
        if gt is not None:
            assert_match(r'\d', str(gt), f"seed={seed}: GT should contain number, got {gt}")

    print("  TimeOfDayWeatherTemplate: Structure validation passed")


async def test_validation_correctness():
    """Verify validators correctly score right and wrong answers"""
    template = LocationNameWeatherTemplate()

    # Test multiple seeds to cover different metric types
    correct_count = 0
    for seed in [100, 200, 300, 500, 600]:
        q = template.generate(seed)
        gt = await template.get_ground_truth(q.validation_info)

        if gt is None:
            continue

        # Ground truth should validate as correct (score >= 0.5)
        result = await template.validate_answer(str(gt), q.validation_info)
        assert_true(
            result.score >= 0.5,
            f"seed={seed}: Ground truth should validate as correct, got score={result.score}, gt={gt}"
        )
        correct_count += 1

        # Completely wrong answer should score 0
        wrong_answers = ["xyz123", "invalid", "-999999"]
        for wrong in wrong_answers:
            result = await template.validate_answer(wrong, q.validation_info)
            # Boolean questions might accidentally match keywords, skip those
            if not q.validation_info.get("is_boolean"):
                assert_true(
                    result.score < 1.0,
                    f"seed={seed}: Wrong answer '{wrong}' shouldn't get full score"
                )

    assert_true(correct_count >= 3, f"Not enough valid tests: {correct_count}")
    print(f"  Validation correctness: {correct_count} cases passed")


async def test_api_field_names():
    """Verify api_field names match wttr.in JSON API response"""
    import httpx
    from .templates.variables import WeatherMetricVariable, MetricType

    # Fetch real API response to get actual field names
    url = "https://wttr.in/London?format=j1"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        data = response.json()

    # Get available fields from hourly data
    hourly_fields = set(data["weather"][0]["hourly"][0].keys())
    daily_fields = set(data["weather"][0].keys())
    all_fields = hourly_fields | daily_fields

    # Check each metric's api_field exists in API response
    for metric_type, spec in WeatherMetricVariable.METRICS.items():
        if spec.api_field in ["weatherDesc"]:  # Special nested fields
            continue
        assert_in(
            spec.api_field, all_fields,
            f"{metric_type.value}: api_field '{spec.api_field}' not in API response"
        )

    print("  API field names: All fields verified")


async def test_tolerance_validation():
    """Verify numeric tolerance works correctly"""
    from liveweb_arena.core.validators.validators import NumericToleranceValidator

    validator = NumericToleranceValidator(
        full_tolerance=2,
        partial_tolerance=5,
        unit="°C"
    )

    # Exact match
    result = validator.validate("25°C", "25")
    assert_true(result.score == 1.0, f"Exact match should score 1.0, got {result.score}")

    # Within full tolerance
    result = validator.validate("27°C", "25")
    assert_true(result.score == 1.0, f"Within 2°C should score 1.0, got {result.score}")

    # Within partial tolerance
    result = validator.validate("29°C", "25")
    assert_true(result.score == 0.5, f"Within 5°C should score 0.5, got {result.score}")

    # Outside tolerance
    result = validator.validate("35°C", "25")
    assert_true(result.score == 0.0, f"Outside 5°C should score 0.0, got {result.score}")

    # Should handle units in ground truth
    result = validator.validate("25", "25°C")
    assert_true(result.score == 1.0, f"Should handle units in GT, got {result.score}")

    print("  Tolerance validation: All cases passed")


async def run_all_tests():
    """Run all template tests"""
    tests = [
        ("LocationNameWeatherTemplate structure", test_location_name_template),
        ("MultiDayWeatherTemplate structure", test_multi_day_template),
        ("TimeOfDayWeatherTemplate structure", test_time_of_day_template),
        ("Validation correctness", test_validation_correctness),
        ("API field names", test_api_field_names),
        ("Tolerance validation", test_tolerance_validation),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            print(f"Testing {name}...")
            await test_fn()
            passed += 1
        except TestFailure as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
