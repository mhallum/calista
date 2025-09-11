"""Functional tests.

Purpose
- Validate user-visible behavior at the system boundary (CLI/API/workflows).

Guidelines
- Treat the system as a black box; avoid asserting internal state.
- Prefer realistic setup with minimal mocking.
- One flow/concern per test; check messages/outputs and side effects.
"""
