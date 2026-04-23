"""Admin-driven order state machine.

Separate from the webhook-driven transitions (PR #12). The admin decides
the fulfilment path — we enforce the legal transitions here and attach an
audit entry for each move.

Allowed paths::

    paid     ──► queued ──► printing ──► shipped ──► delivered
       │            │            │
       ▼            ▼            ▼
    cancelled   cancelled    cancelled

Refunds are a separate mutation (``admin.refund_order``) — they can
originate from ``paid``, ``queued``, ``printing``, ``shipped`` or
``delivered`` and always produce ``refunded``.
"""

from __future__ import annotations

from app.exceptions import BusinessRuleViolation

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"cancelled"},
    "paid": {"queued", "cancelled"},
    "queued": {"printing", "cancelled"},
    "printing": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
    "refunded": set(),
}

REFUNDABLE_FROM = {"paid", "queued", "printing", "shipped", "delivered"}


def assert_transition_allowed(current: str, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise BusinessRuleViolation(
            f"Transición no permitida: {current} → {target}.",
            details={"from": current, "to": target},
        )


def assert_refund_allowed(current: str) -> None:
    if current not in REFUNDABLE_FROM:
        raise BusinessRuleViolation(
            f"No se puede reembolsar un pedido en estado {current}.",
            details={"from": current},
        )
