"""Transactional email stubs.

All senders are fire-and-forget and MUST NOT raise — an email failure
can never block a database transition. In dev (no ``RESEND_API_KEY``),
we log structured payloads so QA can inspect them without SMTP.
"""
