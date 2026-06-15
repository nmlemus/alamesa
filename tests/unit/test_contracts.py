from shared.contracts import (
    ACTOR_PERMISSIONS,
    LEGAL_TRANSITIONS,
    OrderStatus,
)

_TERMINAL_STATES = {OrderStatus.CLOSED, OrderStatus.CANCELLED}


def test_all_statuses_covered_in_legal_transitions() -> None:
    assert set(LEGAL_TRANSITIONS.keys()) == set(OrderStatus)


def test_terminal_states_have_empty_transitions() -> None:
    for state in _TERMINAL_STATES:
        assert LEGAL_TRANSITIONS[state] == set(), (
            f"{state} is terminal but has outgoing transitions"
        )


def test_non_terminal_states_have_at_least_one_transition() -> None:
    for state in OrderStatus:
        if state not in _TERMINAL_STATES:
            assert LEGAL_TRANSITIONS[state], (
                f"{state} is non-terminal but has no outgoing transitions"
            )


def test_actor_permissions_align_with_legal_transitions() -> None:
    for (from_status, to_status) in ACTOR_PERMISSIONS:
        assert to_status in LEGAL_TRANSITIONS[from_status], (
            f"({from_status} -> {to_status}) in ACTOR_PERMISSIONS "
            "but not in LEGAL_TRANSITIONS"
        )


def test_every_legal_transition_has_actor_permissions() -> None:
    for from_status, to_statuses in LEGAL_TRANSITIONS.items():
        for to_status in to_statuses:
            assert (from_status, to_status) in ACTOR_PERMISSIONS, (
                f"({from_status} -> {to_status}) is a legal transition "
                "but missing from ACTOR_PERMISSIONS"
            )


def test_actor_permissions_sets_are_non_empty() -> None:
    for transition, actors in ACTOR_PERMISSIONS.items():
        assert actors, f"ACTOR_PERMISSIONS[{transition}] is an empty set"
