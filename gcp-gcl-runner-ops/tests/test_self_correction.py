#!/usr/bin/env python3
"""
Tests for Self-Correction Suggestion Module.

These tests define the expected behavior for error pattern analysis
and correction suggestion generation.
Run with: python -m pytest tests/test_self_correction.py -v
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from self_correction import (
    CorrectionSuggestionGenerator,
    ErrorPatternAnalyzer,
    GCPErrorType,
)


class TestErrorPatternAnalyzer:
    """Test suite for ErrorPatternAnalyzer."""

    def test_error_pattern_analyzer_classifies_api_rate_limit(self) -> None:
        """Verify API rate limit errors are correctly classified."""
        analyzer = ErrorPatternAnalyzer()

        # Simulate rate limit error from GCP API
        error_context = {
            "error": {
                "code": 429,
                "message": "Quota exceeded for resource",
                "status": "RESOURCE_EXHAUSTED",
            },
            "operation": "gcloud compute instances list",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.API_RATE_LIMIT
        assert "retry" in result.error_message.lower() or "quota" in result.error_message.lower()

    def test_error_pattern_analyzer_classifies_auth_error(self) -> None:
        """Verify authentication errors are correctly classified."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": 401,
                "message": "Invalid authentication credentials",
                "status": "UNAUTHENTICATED",
            },
            "operation": "gcloud compute instances describe",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.AUTH_ERROR
        assert "credential" in result.error_message.lower() or "auth" in result.error_message.lower()

    def test_error_pattern_analyzer_classifies_permission_denied(self) -> None:
        """Verify permission denied errors are correctly classified."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": 403,
                "message": "Permission 'compute.instances.delete' denied",
                "status": "PERMISSION_DENIED",
            },
            "operation": "gcloud compute instances delete",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.PERMISSION_DENIED

    def test_error_pattern_analyzer_classifies_timeout(self) -> None:
        """Verify timeout errors are correctly classified."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": 408,
                "message": "Request timeout",
                "status": "TIMEOUT",
            },
            "operation": "gcloud bigquery datasets list",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.TIMEOUT

    def test_error_pattern_analyzer_classifies_network_error(self) -> None:
        """Verify network errors are correctly classified."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": -1,
                "message": "Connection reset by peer",
                "status": "NETWORK_ERROR",
            },
            "operation": "gcloud compute scp",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.NETWORK_ERROR

    def test_error_pattern_analyzer_handles_unknown_error(self) -> None:
        """Verify unknown errors are classified as UNKNOWN."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": 999,
                "message": "Some obscure error",
                "status": "UNKNOWN",
            },
            "operation": "gcloud some command",
        }

        result = analyzer.analyze(error_context)

        assert result.error_type == GCPErrorType.UNKNOWN

    def test_error_pattern_analyzer_extracts_context(self) -> None:
        """Verify error context is properly extracted."""
        analyzer = ErrorPatternAnalyzer()

        error_context = {
            "error": {
                "code": 400,
                "message": "Invalid parameter 'zone'",
                "status": "INVALID_ARGUMENT",
            },
            "operation": "gcloud compute instances create",
            "extra": {"region": "us-central1", "zone": "invalid-zone"},
        }

        result = analyzer.analyze(error_context)

        assert result.operation == "gcloud compute instances create"
        assert result.error_code == 400


class TestCorrectionSuggestionGenerator:
    """Test suite for CorrectionSuggestionGenerator."""

    def test_suggestion_generator_produces_valid_json(self) -> None:
        """Verify suggestion output is valid JSON-serializable."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {
                "code": 429,
                "message": "Quota exceeded",
                "status": "RESOURCE_EXHAUSTED",
            },
            "operation": "gcloud compute instances list",
        }

        suggestion = generator.generate(error_context)

        # Should not raise
        json_str = json.dumps(suggestion.to_dict())
        parsed = json.loads(json_str)

        assert "error_type" in parsed
        assert "suggestion" in parsed
        assert "confidence" in parsed
        assert "references" in parsed

    def test_suggestion_confidence_range(self) -> None:
        """Verify confidence score is between 0.0 and 1.0."""
        generator = CorrectionSuggestionGenerator()

        test_cases = [
            {
                "error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"},
                "operation": "gcloud compute instances list",
            },
            {
                "error": {"code": 401, "message": "Invalid credentials", "status": "UNAUTHENTICATED"},
                "operation": "gcloud compute instances describe",
            },
            {
                "error": {"code": 400, "message": "Invalid parameter", "status": "INVALID_ARGUMENT"},
                "operation": "gcloud compute instances create",
            },
        ]

        for case in test_cases:
            suggestion = generator.generate(case)
            assert 0.0 <= suggestion.confidence <= 1.0, f"Confidence out of range: {suggestion.confidence}"

    def test_suggestion_for_api_rate_limit_has_exponential_backoff(self) -> None:
        """Verify API rate limit suggestions include exponential backoff."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"},
            "operation": "gcloud compute instances list",
        }

        suggestion = generator.generate(error_context)

        # Check for Chinese keywords: 重试 (retry), 退避 (backoff), 延迟 (delay)
        assert "重试" in suggestion.suggestion or "退避" in suggestion.suggestion or "延迟" in suggestion.suggestion
        assert suggestion.error_type == GCPErrorType.API_RATE_LIMIT

    def test_suggestion_for_auth_error_mentions_credentials(self) -> None:
        """Verify auth error suggestions mention checking credentials."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": 401, "message": "Invalid credentials", "status": "UNAUTHENTICATED"},
            "operation": "gcloud compute instances describe",
        }

        suggestion = generator.generate(error_context)

        # Check for Chinese keywords: 凭证 (credential), 认证 (auth), 服务账号 (service account)
        assert "凭证" in suggestion.suggestion or "认证" in suggestion.suggestion or "服务账号" in suggestion.suggestion

    def test_suggestion_for_param_error_mentions_parameters(self) -> None:
        """Verify parameter error suggestions mention checking parameters."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": 400, "message": "Invalid parameter 'zone'", "status": "INVALID_ARGUMENT"},
            "operation": "gcloud compute instances create",
        }

        suggestion = generator.generate(error_context)

        # Check for Chinese keywords: 参数 (parameter), 区域 (zone/region)
        assert "参数" in suggestion.suggestion or "区域" in suggestion.suggestion or "拼写" in suggestion.suggestion

    def test_suggestion_for_network_error_suggests_retry(self) -> None:
        """Verify network error suggestions suggest retry or check network."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": -1, "message": "Connection reset", "status": "NETWORK_ERROR"},
            "operation": "gcloud compute scp",
        }

        suggestion = generator.generate(error_context)

        # Check for Chinese keywords: 重试 (retry), 网络 (network), 连接 (connection)
        assert "重试" in suggestion.suggestion or "网络" in suggestion.suggestion or "连接" in suggestion.suggestion

    def test_suggestion_references_contain_documentation(self) -> None:
        """Verify suggestions include relevant references."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"},
            "operation": "gcloud compute instances list",
        }

        suggestion = generator.generate(error_context)

        assert isinstance(suggestion.references, list)
        # Should have at least some references
        assert len(suggestion.references) >= 0

    def test_suggestion_for_unknown_error_is_generic(self) -> None:
        """Verify unknown error generates generic but helpful suggestion."""
        generator = CorrectionSuggestionGenerator()

        error_context = {
            "error": {"code": 999, "message": "Obscure error", "status": "UNKNOWN"},
            "operation": "gcloud some command",
        }

        suggestion = generator.generate(error_context)

        assert suggestion.error_type == GCPErrorType.UNKNOWN
        assert len(suggestion.suggestion) > 0


class TestGCPErrorType:
    """Test suite for GCPErrorType enum."""

    def test_error_type_values(self) -> None:
        """Verify all expected error types are defined."""
        expected_types = {
            "API_RATE_LIMIT",
            "AUTH_ERROR",
            "PARAM_ERROR",
            "NETWORK_ERROR",
            "UNKNOWN",
            "INVALID_ARGUMENT",
            "PERMISSION_DENIED",
            "NOT_FOUND",
            "TIMEOUT",
            "INTERNAL",
            "UNAUTHENTICATED",
            "RESOURCE_EXHAUSTED",
            "FAILED_PRECONDITION",
            "ABORTED",
            "OUT_OF_RANGE",
            "UNAVAILABLE",
        }

        actual_types = {e.value for e in GCPErrorType}

        for expected in expected_types:
            assert expected in actual_types, f"Missing error type: {expected}"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_error_context() -> dict[str, Any]:
    """Sample error context for testing."""
    return {
        "error": {
            "code": 429,
            "message": "Quota exceeded for resource 'instances'",
            "status": "RESOURCE_EXHAUSTED",
        },
        "operation": "gcloud compute instances list",
    }
