"""Tests for fail-loud false-positive filtering.

Regression cover for the defect these tests were written against: FindingsFilter used
to open with a fixed-model probe (validate_api_access, hard-coded to a model id that
was later retired). When the probe failed, filtering was silently switched off and the
audit reported hard-rules-only output as though the Claude filter had passed it. There
is no probe any more, and a configuration-class failure raises instead of degrading.
"""

import pytest
from unittest.mock import patch

from claudecode.claude_api_client import (
    ClaudeAPIClient,
    ClaudeFilteringUnavailableError,
    is_configuration_error,
)
from claudecode.findings_filter import FindingsFilter


# A placeholder id, not a real retired one: test_no_retired_model_ids.py scans the whole
# tree, and a literal retired id here would be a (correct) hit on a test fixture.
NOT_FOUND = (
    "Error code: 404 - {'type': 'error', 'error': {'type': 'not_found_error', "
    "'message': 'model: claude-some-retired-model-00000000'}}"
)
RATE_LIMITED = (
    "Error code: 429 - {'type': 'error', 'error': {'type': 'rate_limit_error', "
    "'message': 'Number of requests has exceeded your rate limit'}}"
)
SPEND_CAP = (
    "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
    "'message': 'API Error: 400 You have reached your specified workspace API usage "
    "limits. You will regain access on 2026-09-30 at 00:00 UTC.'}}"
)

A_FINDING = {
    'file': 'app/db.py',
    'line': 42,
    'severity': 'HIGH',
    'category': 'injection',
    'description': 'SQL injection: user input concatenated into a query string',
}


class TestConfigurationErrorClassification:
    """The classifier must be narrow: config errors only, never transient/billing."""

    @pytest.mark.parametrize('message', [
        NOT_FOUND,
        "Error code: 401 - {'error': {'type': 'authentication_error'}}",
        "Error code: 403 - {'error': {'type': 'permission_error'}}",
        "invalid x-api-key",
    ])
    def test_configuration_errors_are_detected(self, message):
        assert is_configuration_error(message) is True

    @pytest.mark.parametrize('message', [
        RATE_LIMITED,
        SPEND_CAP,
        "Error code: 529 - {'error': {'type': 'overloaded_error'}}",
        "Request timed out.",
        "Your credit balance is too low to access the Anthropic API.",
        "Connection error.",
        "",
    ])
    def test_transient_and_billing_errors_are_not_configuration_errors(self, message):
        assert is_configuration_error(message) is False


class TestNoStartupProbe:
    """Constructing the filter must not make an API call of its own."""

    def test_construction_makes_no_api_call(self):
        with patch('claudecode.claude_api_client.Anthropic') as anthropic:
            findings_filter = FindingsFilter(
                use_claude_filtering=True, api_key='test-key', model='claude-opus-5')
            assert findings_filter.use_claude_filtering is True
            assert findings_filter.claude_client is not None
            assert anthropic.return_value.messages.create.call_count == 0

    def test_client_has_no_validate_api_access(self):
        assert not hasattr(ClaudeAPIClient, 'validate_api_access')


class TestFailLoud:
    """A configuration-class failure must abort, never silently disable filtering."""

    def test_not_found_raises_instead_of_disabling_filtering(self):
        with patch('claudecode.claude_api_client.Anthropic') as anthropic, \
                patch('claudecode.claude_api_client.time.sleep'):
            anthropic.return_value.messages.create.side_effect = RuntimeError(NOT_FOUND)
            findings_filter = FindingsFilter(
                use_claude_filtering=True, api_key='test-key', model='claude-opus-5')
            with pytest.raises(ClaudeFilteringUnavailableError) as excinfo:
                findings_filter.filter_findings([dict(A_FINDING)])
            assert 'claude-opus-5' in str(excinfo.value)
            # Raised on the FIRST failure: no retry storm against an unknown model id.
            assert anthropic.return_value.messages.create.call_count == 1

    def test_transient_error_still_degrades_gracefully(self):
        """Guards the classifier's narrowness: rate limits must NOT fail the run."""
        with patch('claudecode.claude_api_client.Anthropic') as anthropic, \
                patch('claudecode.claude_api_client.time.sleep'):
            anthropic.return_value.messages.create.side_effect = RuntimeError(RATE_LIMITED)
            findings_filter = FindingsFilter(
                use_claude_filtering=True, api_key='test-key', model='claude-opus-5')
            success, results, stats = findings_filter.filter_findings([dict(A_FINDING)])
            assert success is True
            assert len(results['filtered_findings']) == 1
            assert anthropic.return_value.messages.create.call_count > 1

    def test_spend_cap_error_still_degrades_gracefully(self):
        with patch('claudecode.claude_api_client.Anthropic') as anthropic, \
                patch('claudecode.claude_api_client.time.sleep'):
            anthropic.return_value.messages.create.side_effect = RuntimeError(SPEND_CAP)
            findings_filter = FindingsFilter(
                use_claude_filtering=True, api_key='test-key', model='claude-opus-5')
            success, results, stats = findings_filter.filter_findings([dict(A_FINDING)])
            assert success is True
            assert len(results['filtered_findings']) == 1
