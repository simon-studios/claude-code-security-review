"""Anthropic model ids that are past their published retirement date.

Sourced from Anthropic's model-deprecations page. A retired id does not resolve: the
API answers `not_found_error`, so any code path that names one is dead code the moment
the date passes. This module exists so that fact is asserted by a test rather than
rediscovered from a bill (see test_no_retired_model_ids.py).

Add an id here on the day it retires. Removing one is never correct — retirements do
not un-happen.

Consumers scanning a whole fleet: this file is exempt (model-id-sweep:allow-whole-file)
— naming retired ids is its job.
"""

# Past their published retirement date (as of 2026-09-03).
RETIRED_MODEL_IDS = (
    'claude-2.0',                      # retired 2025-07-21
    'claude-2.1',                      # retired 2025-07-21
    'claude-3-sonnet-20240229',        # retired 2025-07-21
    'claude-3-5-sonnet-20240620',      # retired 2025-10-28
    'claude-3-5-sonnet-20241022',      # retired 2025-10-28
    'claude-3-opus-20240229',          # retired 2026-01-05
    'claude-3-5-haiku-20241022',       # retired 2026-02-19  <- the probe id this repo shipped
    'claude-3-7-sonnet-20250219',      # retired 2026-02-19
    'claude-3-haiku-20240307',         # retired 2026-04-19
    'claude-opus-4-1-20250805',        # retired 2026-08-05
)

# Announced deprecated, still served, retirement date not yet published. Not asserted
# against — listed so the next person does not have to re-derive the boundary.
DEPRECATED_MODEL_IDS = (
    'claude-opus-4-20250514',
    'claude-sonnet-4-20250514',
)
