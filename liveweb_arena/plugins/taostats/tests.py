"""Tests for Taostats plugin - validates template correctness across all variations"""

import asyncio
import re
from .templates import SubnetInfoTemplate, SubnetVariable, MetricVariable, SubnetMetric


class TestFailure(Exception):
    pass


def assert_true(condition, msg):
    if not condition:
        raise TestFailure(msg)


def assert_in(item, collection, msg):
    if item not in collection:
        raise TestFailure(f"{msg}: {item} not in {collection}")


def assert_match(pattern, text, msg):
    if not re.search(pattern, text, re.IGNORECASE):
        raise TestFailure(f"{msg}: '{text}' doesn't match '{pattern}'")


async def test_subnet_variable_coverage():
    """Verify SubnetVariable covers active subnets from network"""
    var = SubnetVariable()

    # Should have subnets fetched from network (dynamically determined)
    assert_true(len(var.subnet_ids) >= 1, f"Expected at least 1 subnet, got {len(var.subnet_ids)}")
    assert_true(len(var.subnet_ids) <= 128, f"Should not exceed 128 subnets, got {len(var.subnet_ids)}")
    assert_true(min(var.subnet_ids) >= 1, "Should not include root network (0)")

    # Test sampling diversity
    import random
    seen = set()
    for seed in range(200):
        rng = random.Random(seed)
        spec = var.sample(rng)
        seen.add(spec.subnet_id)

    # Should sample at least 75% of available subnets with 200 samples
    min_expected = min(len(var.subnet_ids) * 0.75, 40)
    assert_true(len(seen) >= min_expected, f"Should sample diverse subnets, got {len(seen)} out of {len(var.subnet_ids)}")
    print(f"  SubnetVariable coverage: {len(var.subnet_ids)} active subnets")


async def test_metric_variable_coverage():
    """Verify MetricVariable covers all metric types"""
    var = MetricVariable()

    # Should have all 7 metrics (name, owner, emission, registration_cost, price, tempo, github_repo)
    assert_true(len(var.allowed_metrics) == 7, f"Expected 7 metrics, got {len(var.allowed_metrics)}")

    # Test sampling covers all metrics
    import random
    seen = set()
    for seed in range(100):
        rng = random.Random(seed)
        spec = var.sample(rng)
        seen.add(spec.metric)

    assert_true(len(seen) == 7, f"Should sample all 7 metrics, got {len(seen)}")
    print("  MetricVariable coverage: passed")


async def test_question_format_name():
    """Verify NAME metric questions are properly formatted"""
    template = SubnetInfoTemplate()

    for seed in range(100, 200, 10):
        q = template.generate(seed)
        if q.validation_info["metric"] == "name":
            # Question should ask about name
            assert_match(r"name|called", q.question_text,
                f"seed={seed}: NAME question should ask about name")
            # Should mention subnet
            assert_match(r"subnet|sn\d+", q.question_text,
                f"seed={seed}: Should mention subnet")

    print("  Question format (NAME): passed")


async def test_question_format_owner():
    """Verify OWNER metric questions are properly formatted"""
    template = SubnetInfoTemplate()

    for seed in range(200, 300, 10):
        q = template.generate(seed)
        if q.validation_info["metric"] == "owner":
            # Question should ask about owner
            assert_match(r"own|address", q.question_text,
                f"seed={seed}: OWNER question should ask about owner")

    print("  Question format (OWNER): passed")


async def test_question_format_numeric():
    """Verify numeric metric questions are properly formatted"""
    template = SubnetInfoTemplate()
    numeric_metrics = {"emission", "registration_cost", "price"}

    for seed in range(300, 500, 10):
        q = template.generate(seed)
        metric = q.validation_info["metric"]
        is_numeric = q.validation_info["is_numeric"]

        if metric in numeric_metrics:
            assert_true(is_numeric, f"seed={seed}: {metric} should be numeric")
            # Should have tolerance set
            assert_true(q.validation_info.get("tolerance_pct", 0) > 0,
                f"seed={seed}: {metric} should have tolerance")

    print("  Question format (numeric): passed")


async def test_url_format():
    """Verify generated URLs point to correct subnet pages"""
    template = SubnetInfoTemplate()

    for seed in range(500, 600, 5):
        q = template.generate(seed)
        subnet_id = q.validation_info["subnet_id"]

        # URL should contain subnet ID
        expected_url = f"https://taostats.io/subnets/{subnet_id}"
        assert_true(q.start_url == expected_url,
            f"seed={seed}: URL mismatch. Got {q.start_url}, expected {expected_url}")

    print("  URL format: passed")


async def test_validation_info_completeness():
    """Verify validation_info has all required fields"""
    template = SubnetInfoTemplate()
    required_fields = {"subnet_id", "metric", "is_numeric", "unit", "tolerance_pct"}

    for seed in range(600, 700, 5):
        q = template.generate(seed)

        for field in required_fields:
            assert_true(field in q.validation_info,
                f"seed={seed}: Missing field '{field}' in validation_info")

        # subnet_id should be valid (1-127 range, excluding root network 0)
        subnet_id = q.validation_info["subnet_id"]
        assert_true(1 <= subnet_id <= 127,
            f"seed={seed}: Invalid subnet_id {subnet_id}")

        # metric should be valid
        metric = q.validation_info["metric"]
        valid_metrics = {m.value for m in SubnetMetric}
        assert_in(metric, valid_metrics,
            f"seed={seed}: Invalid metric")

    print("  Validation info completeness: passed")


async def test_question_diversity():
    """Verify questions have sufficient diversity across seeds"""
    template = SubnetInfoTemplate()

    questions = set()
    subnets = set()
    metrics = set()

    for seed in range(1000):
        q = template.generate(seed)
        questions.add(q.question_text)
        subnets.add(q.validation_info["subnet_id"])
        metrics.add(q.validation_info["metric"])

    # Should generate diverse questions
    assert_true(len(questions) >= 200,
        f"Should generate 200+ unique questions, got {len(questions)}")
    # Should cover most available subnets (at least 75% or 40, whichever is smaller)
    var = SubnetVariable()
    min_subnets = min(int(len(var.subnet_ids) * 0.75), 40)
    assert_true(len(subnets) >= min_subnets,
        f"Should cover {min_subnets}+ subnets, got {len(subnets)}")
    assert_true(len(metrics) == 7,
        f"Should cover all 7 metrics, got {len(metrics)}")

    print(f"  Question diversity: {len(questions)} unique questions, "
          f"{len(subnets)} subnets, {len(metrics)} metrics")


async def test_validation_rules():
    """Verify validation rules are generated correctly"""
    template = SubnetInfoTemplate()

    for seed in [100, 200, 300, 400, 500]:
        q = template.generate(seed)
        rules = template.get_validation_rules(q.validation_info)

        metric = q.validation_info["metric"]
        is_numeric = q.validation_info["is_numeric"]

        if metric == "name":
            assert_match(r"name", rules, f"seed={seed}: NAME rules should mention name")
        elif metric == "owner":
            assert_match(r"address", rules, f"seed={seed}: OWNER rules should mention address")
        elif metric == "tempo":
            assert_match(r"exact", rules, f"seed={seed}: TEMPO rules should mention exact match")
        elif metric == "github_repo":
            assert_match(r"URL", rules, f"seed={seed}: GITHUB_REPO rules should mention URL")
        elif is_numeric:
            assert_match(r"tolerance", rules, f"seed={seed}: Numeric rules should mention tolerance")

    print("  Validation rules: passed")


async def test_ground_truth_name():
    """Verify ground truth fetch for subnet names works"""
    template = SubnetInfoTemplate()

    # Test known subnet - subnet 27 should be "Nodexo"
    validation_info = {"subnet_id": 27, "metric": "name"}
    gt = await template.get_ground_truth(validation_info)

    assert_true(gt is not None, "Ground truth should not be None for valid subnet")
    assert_true(isinstance(gt, str), "Subnet name should be a string")
    assert_true(len(gt) > 0, "Subnet name should not be empty")

    print(f"  Ground truth (name): subnet 27 = '{gt}'")


async def test_ground_truth_owner():
    """Verify ground truth fetch for subnet owners works"""
    template = SubnetInfoTemplate()

    validation_info = {"subnet_id": 1, "metric": "owner"}
    gt = await template.get_ground_truth(validation_info)

    assert_true(gt is not None, "Ground truth should not be None")
    assert_true(gt.startswith("5"), "Bittensor addresses start with 5")
    assert_true(len(gt) > 40, "Address should be full length")

    print(f"  Ground truth (owner): subnet 1 = '{gt[:20]}...'")


async def test_validation_correctness():
    """Verify validation correctly scores matching and non-matching answers"""
    template = SubnetInfoTemplate()

    # Test name validation
    validation_info = {"subnet_id": 27, "metric": "name"}
    gt = await template.get_ground_truth(validation_info)

    if gt:
        # Correct answer should score 1.0
        result = await template.validate_answer(gt, validation_info)
        assert_true(result.score == 1.0, f"Exact match should score 1.0, got {result.score}")

        # Wrong answer should score 0.0
        result = await template.validate_answer("WrongName", validation_info)
        assert_true(result.score == 0.0, f"Wrong answer should score 0.0, got {result.score}")

    print("  Validation correctness: passed")


async def run_all_tests():
    """Run all template tests"""
    # Basic tests (no network required)
    tests = [
        ("SubnetVariable coverage", test_subnet_variable_coverage),
        ("MetricVariable coverage", test_metric_variable_coverage),
        ("Question format (NAME)", test_question_format_name),
        ("Question format (OWNER)", test_question_format_owner),
        ("Question format (numeric)", test_question_format_numeric),
        ("URL format", test_url_format),
        ("Validation info completeness", test_validation_info_completeness),
        ("Question diversity", test_question_diversity),
        ("Validation rules", test_validation_rules),
        # Network tests (require Bittensor connection)
        ("Ground truth (name)", test_ground_truth_name),
        ("Ground truth (owner)", test_ground_truth_owner),
        ("Validation correctness", test_validation_correctness),
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
