"""
Self-Correction Suggestion Module for GCL Runner.

This module provides error pattern analysis and correction suggestion generation
for GCP operations executed through the GCL framework.

Version: 1.0.0
Updated: 2026-07-19
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GCPErrorType(str, Enum):
    """Valid GCP error types including self-correction specific types."""

    # Self-correction specific types (mapped from GCP API errors)
    API_RATE_LIMIT = "API_RATE_LIMIT"
    AUTH_ERROR = "AUTH_ERROR"
    PARAM_ERROR = "PARAM_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"

    # Standard GCP API error types
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ErrorPatternResult:
    """Result of error pattern analysis."""

    error_type: GCPErrorType
    error_code: int
    error_message: str
    operation: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class SuggestionOutput:
    """Structured output for correction suggestions."""

    error_type: str
    suggestion: str
    confidence: float  # 0.0 - 1.0
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_type": self.error_type,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "references": self.references,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ErrorPatternAnalyzer:
    """
    Analyzes error patterns from GCL trace and operation contexts.

    Identifies error types and extracts relevant context for generating
    correction suggestions.
    """

    # Mapping from GCP status/code to GCPErrorType
    STATUS_MAPPING: dict[str, GCPErrorType] = {
        "RESOURCE_EXHAUSTED": GCPErrorType.API_RATE_LIMIT,
        "QUOTA_EXCEEDED": GCPErrorType.API_RATE_LIMIT,
        "RATE_LIMITED": GCPErrorType.API_RATE_LIMIT,
        "UNAUTHENTICATED": GCPErrorType.AUTH_ERROR,
        "INVALID_CREDENTIALS": GCPErrorType.AUTH_ERROR,
        "AUTH_ERROR": GCPErrorType.AUTH_ERROR,
        "PERMISSION_DENIED": GCPErrorType.PERMISSION_DENIED,
        "FORBIDDEN": GCPErrorType.PERMISSION_DENIED,
        "INVALID_ARGUMENT": GCPErrorType.PARAM_ERROR,
        "BAD_PARAMETER": GCPErrorType.PARAM_ERROR,
        "INVALID_PARAMETER": GCPErrorType.PARAM_ERROR,
        "NETWORK_ERROR": GCPErrorType.NETWORK_ERROR,
        "CONNECTION_ERROR": GCPErrorType.NETWORK_ERROR,
        "TIMEOUT": GCPErrorType.TIMEOUT,
        "DEADLINE_EXCEEDED": GCPErrorType.TIMEOUT,
        "NOT_FOUND": GCPErrorType.NOT_FOUND,
        "INTERNAL": GCPErrorType.INTERNAL,
        "UNKNOWN": GCPErrorType.UNKNOWN,
        "UNAVAILABLE": GCPErrorType.UNAVAILABLE,
    }

    # HTTP status codes mapping
    HTTP_CODE_MAPPING: dict[int, GCPErrorType] = {
        400: GCPErrorType.PARAM_ERROR,
        401: GCPErrorType.AUTH_ERROR,
        403: GCPErrorType.PERMISSION_DENIED,
        404: GCPErrorType.NOT_FOUND,
        408: GCPErrorType.TIMEOUT,
        429: GCPErrorType.API_RATE_LIMIT,
        500: GCPErrorType.INTERNAL,
        502: GCPErrorType.NETWORK_ERROR,
        503: GCPErrorType.UNAVAILABLE,
        504: GCPErrorType.TIMEOUT,
    }

    def analyze(self, error_context: dict[str, Any]) -> ErrorPatternResult:
        """
        Analyze error context and classify the error type.

        Args:
            error_context: Dict containing 'error' and 'operation' keys.
                error: Dict with 'code', 'message', 'status' fields.
                operation: The gcloud command that failed.

        Returns:
            ErrorPatternResult with classified error type and context.
        """
        error = error_context.get("error", {})
        operation = error_context.get("operation", "")

        error_code = error.get("code", -1)
        error_message = error.get("message", "")
        status = error.get("status", "")

        # Try to classify based on status string
        error_type = self._classify_by_status(status, error_message)

        # Fall back to HTTP code mapping if not classified
        if error_type == GCPErrorType.UNKNOWN and error_code in self.HTTP_CODE_MAPPING:
            error_type = self.HTTP_CODE_MAPPING[error_code]

        return ErrorPatternResult(
            error_type=error_type,
            error_code=error_code,
            error_message=error_message,
            operation=operation,
            context=error_context,
        )

    def _classify_by_status(self, status: str, message: str) -> GCPErrorType:
        """Classify error based on status string and message content."""
        if not status:
            # Try to infer from message
            message_lower = message.lower()
            if any(kw in message_lower for kw in ["rate limit", "quota", "exhausted"]):
                return GCPErrorType.API_RATE_LIMIT
            if any(kw in message_lower for kw in ["auth", "credential", "token", "unauthenticated"]):
                return GCPErrorType.AUTH_ERROR
            if any(kw in message_lower for kw in ["permission", "denied", "forbidden"]):
                return GCPErrorType.PERMISSION_DENIED
            if any(kw in message_lower for kw in ["network", "connection", "reset"]):
                return GCPErrorType.NETWORK_ERROR
            if any(kw in message_lower for kw in ["timeout", "timed out"]):
                return GCPErrorType.TIMEOUT
            if any(kw in message_lower for kw in ["invalid", "parameter", "argument"]):
                return GCPErrorType.PARAM_ERROR
            return GCPErrorType.UNKNOWN

        # Direct status mapping
        if status in self.STATUS_MAPPING:
            return self.STATUS_MAPPING[status]

        # Try partial match
        status_upper = status.upper()
        for key, value in self.STATUS_MAPPING.items():
            if key in status_upper:
                return value

        return GCPErrorType.UNKNOWN


class CorrectionSuggestionGenerator:
    """
    Generates correction suggestions based on error analysis.

    Produces structured JSON output with specific suggestions,
    confidence scores, and references.
    """

    # Suggestion templates by error type
    SUGGESTIONS: dict[GCPErrorType, tuple[str, float, list[str]]] = {
        GCPErrorType.API_RATE_LIMIT: (
            "建议使用指数退避策略重试。初始延迟建议 1 秒，之后每次重试延迟翻倍，最大延迟不超过 64 秒。"
            "考虑使用 --on-behalf-of 参数或在非高峰时段执行操作。",
            0.95,
            [
                "https://cloud.google.com/apis/docs/error-handling",
                "https://cloud.google.com/resource-manager/reference/rest/v1/projects",
            ],
        ),
        GCPErrorType.AUTH_ERROR: (
            "请检查服务账号凭证是否有效且未过期。验证 GOOGLE_APPLICATION_CREDENTIALS 环境变量"
            "指向正确的密钥文件，或使用 'gcloud auth login' 重新认证。",
            0.95,
            [
                "https://cloud.google.com/docs/authentication/getting-started",
                "https://cloud.google.com/iam/docs/creating-managing-service-account-keys",
            ],
        ),
        GCPErrorType.PERMISSION_DENIED: (
            "当前服务账号缺少必要权限。请使用 'gcloud projects add-iam-policy-binding' 添加所需角色，"
            "或检查资源级 IAM 条件是否阻止了操作。",
            0.90,
            [
                "https://cloud.google.com/iam/docs/understanding-roles",
                "https://cloud.google.com/iam/docs/conditions",
            ],
        ),
        GCPErrorType.PARAM_ERROR: (
            "请检查命令参数是否正确。验证区域/可用区 (zone/region) 拼写、值是否在有效范围内，"
            "以及必需参数是否已提供。使用 --help 查看正确语法。",
            0.90,
            [
                "https://cloud.google.com/sdk/gcloud/reference/",
            ],
        ),
        GCPErrorType.NETWORK_ERROR: (
            "网络连接不稳定，建议稍后重试。检查本地网络配置、防火墙规则和 VPN 设置。"
            "对于长时间操作，考虑使用异步执行或增加超时时间。",
            0.85,
            [
                "https://cloud.google.com/network-connectivity/docs/reference/rest",
            ],
        ),
        GCPErrorType.TIMEOUT: (
            "操作超时，可能是资源繁忙或网络延迟。建议重试，或增加超时时间。"
            "对于大数据集操作，考虑使用批处理或异步执行。",
            0.85,
            [
                "https://cloud.google.com/sdk/gcloud/reference",
            ],
        ),
        GCPErrorType.NOT_FOUND: (
            "请求的资源不存在。请检查资源标识符 (name/ID) 是否正确，"
            "以及资源是否在指定的区域/可用区中。",
            0.95,
            [
                "https://cloud.google.com/apis/design/errors",
            ],
        ),
        GCPErrorType.INTERNAL: (
            "GCP 内部服务错误，通常为临时性问题。建议稍后重试，"
            "如果问题持续，请检查 GCP Status Dashboard。",
            0.70,
            [
                "https://status.cloud.google.com/",
                "https://cloud.google.com/apis/design/errors",
            ],
        ),
        GCPErrorType.UNAVAILABLE: (
            "服务暂时不可用。建议稍后重试，或查看 GCP 状态页面确认是否有已知的服务中断。",
            0.80,
            [
                "https://status.cloud.google.com/",
                "https://cloud.google.com/apis/design/errors",
            ],
        ),
        GCPErrorType.UNKNOWN: (
            "遇到未知错误。建议：1) 查阅 gcloud 命令帮助确认参数正确；"
            "2) 使用 --log-http --verbosity=debug 查看详细日志；"
            "3) 尝试简化命令排除参数冲突。",
            0.50,
            [
                "https://cloud.google.com/sdk/gcloud/reference",
                "https://cloud.google.com/apis/design/errors",
            ],
        ),
    }

    def __init__(self) -> None:
        """Initialize the suggestion generator."""
        self.analyzer = ErrorPatternAnalyzer()

    def generate(self, error_context: dict[str, Any]) -> SuggestionOutput:
        """
        Generate a correction suggestion for the given error context.

        Args:
            error_context: Dict containing 'error' and 'operation' keys.

        Returns:
            SuggestionOutput with structured suggestion, confidence, and references.
        """
        analysis = self.analyzer.analyze(error_context)

        template, confidence, references = self.SUGGESTIONS.get(
            analysis.error_type,
            (self.SUGGESTIONS[GCPErrorType.UNKNOWN][0], 0.50, self.SUGGESTIONS[GCPErrorType.UNKNOWN][2]),
        )

        # Customize suggestion with operation context if available
        suggestion = template
        if analysis.operation:
            # Add operation context to suggestion if helpful
            suggestion = self._customize_suggestion(template, analysis)

        return SuggestionOutput(
            error_type=analysis.error_type.value,
            suggestion=suggestion,
            confidence=confidence,
            references=references,
        )

    def _customize_suggestion(
        self, template: str, analysis: ErrorPatternResult
    ) -> str:
        """Customize suggestion template with operation context."""
        operation = analysis.operation

        # Extract relevant parts from operation for context
        if "compute" in operation:
            product = "Compute Engine"
        elif "bigquery" in operation:
            product = "BigQuery"
        elif "storage" in operation or "gs://" in operation:
            product = "Cloud Storage"
        elif "container" in operation or "gke" in operation:
            product = "GKE"
        elif "sql" in operation:
            product = "Cloud SQL"
        elif "logging" in operation:
            product = "Cloud Logging"
        elif "monitoring" in operation or "metrics" in operation:
            product = "Cloud Monitoring"
        else:
            product = "GCP"

        # Replace generic references with product-specific ones
        customized = template.replace("GCP", product)

        # Add operation context if it provides additional insight
        if analysis.error_type == GCPErrorType.API_RATE_LIMIT:
            # Check if this is a list operation which is commonly rate limited
            if " list " in operation or " describe " in operation:
                customized += (
                    f"\n\n对于 {product} 的列表操作，建议使用过滤条件减少返回结果，"
                    "或使用缓存机制减少 API 调用频率。"
                )

        return customized

    def generate_batch(self, error_contexts: list[dict[str, Any]]) -> list[SuggestionOutput]:
        """
        Generate suggestions for multiple error contexts.

        Args:
            error_contexts: List of error context dicts.

        Returns:
            List of SuggestionOutput objects.
        """
        return [self.generate(ctx) for ctx in error_contexts]


# Convenience function for simple usage
def analyze_and_suggest(error_context: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze error and generate suggestion in one call.

    Args:
        error_context: Dict containing 'error' and 'operation' keys.

    Returns:
        Dict with error_type, suggestion, confidence, and references.
    """
    generator = CorrectionSuggestionGenerator()
    result = generator.generate(error_context)
    return result.to_dict()
