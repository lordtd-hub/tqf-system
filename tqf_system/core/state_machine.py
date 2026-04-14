"""
tqf_system/core/state_machine.py
State machine for the course-offering lifecycle.

8 states:
  not_started → in_progress → ready_for_tqf3 → tqf3_generated
  → teaching → grades_imported → ready_for_tqf5 → tqf5_generated → term_closed
"""
from __future__ import annotations

# ── State constants ────────────────────────────────────────────────
NOT_STARTED     = "not_started"
IN_PROGRESS     = "in_progress"
READY_FOR_TQF3  = "ready_for_tqf3"
TQF3_GENERATED  = "tqf3_generated"
TEACHING        = "teaching"
GRADES_IMPORTED = "grades_imported"
READY_FOR_TQF5  = "ready_for_tqf5"
TQF5_GENERATED  = "tqf5_generated"
TERM_CLOSED     = "term_closed"

ALL_STATES: list[str] = [
    NOT_STARTED, IN_PROGRESS, READY_FOR_TQF3, TQF3_GENERATED,
    TEACHING, GRADES_IMPORTED, READY_FOR_TQF5, TQF5_GENERATED, TERM_CLOSED,
]

# ── Thai labels ────────────────────────────────────────────────────
STATE_LABELS_TH: dict[str, str] = {
    NOT_STARTED:     "ยังไม่เริ่ม",
    IN_PROGRESS:     "กำลังดำเนินการ",
    READY_FOR_TQF3:  "พร้อม มคอ.3",
    TQF3_GENERATED:  "มคอ.3 สร้างแล้ว",
    TEACHING:        "กำลังสอน",
    GRADES_IMPORTED: "นำเข้าเกรดแล้ว",
    READY_FOR_TQF5:  "พร้อม มคอ.5",
    TQF5_GENERATED:  "มคอ.5 สร้างแล้ว",
    TERM_CLOSED:     "ปิดภาคเรียน",
}

# ── Color codes for UI chips ──────────────────────────────────────
STATE_COLORS: dict[str, str] = {
    NOT_STARTED:     "#9E9E9E",   # gray
    IN_PROGRESS:     "#1976D2",   # blue
    READY_FOR_TQF3:  "#0288D1",   # light-blue
    TQF3_GENERATED:  "#388E3C",   # green
    TEACHING:        "#F57C00",   # orange
    GRADES_IMPORTED: "#7B1FA2",   # purple
    READY_FOR_TQF5:  "#0097A7",   # teal
    TQF5_GENERATED:  "#2E7D32",   # dark-green
    TERM_CLOSED:     "#455A64",   # blue-gray
}

# ── Allowed transitions: state → [next_states] ────────────────────
TRANSITIONS: dict[str, list[str]] = {
    NOT_STARTED:     [IN_PROGRESS],
    IN_PROGRESS:     [READY_FOR_TQF3, NOT_STARTED],
    READY_FOR_TQF3:  [TQF3_GENERATED, IN_PROGRESS],
    TQF3_GENERATED:  [TEACHING, READY_FOR_TQF3],      # regen allowed
    TEACHING:        [GRADES_IMPORTED],
    GRADES_IMPORTED: [READY_FOR_TQF5, TEACHING],
    READY_FOR_TQF5:  [TQF5_GENERATED, GRADES_IMPORTED],
    TQF5_GENERATED:  [TERM_CLOSED, READY_FOR_TQF5],   # regen allowed
    TERM_CLOSED:     [],                               # terminal
}


class IllegalTransition(Exception):
    """Raised when a requested state transition is not allowed."""


def allowed_next(state: str) -> list[str]:
    """Return the list of states reachable from *state*."""
    return list(TRANSITIONS.get(state, []))


def validate_transition(from_state: str, to_state: str) -> None:
    """Raise IllegalTransition if the transition is not permitted."""
    allowed = TRANSITIONS.get(from_state, [])
    if to_state not in allowed:
        from_label = STATE_LABELS_TH.get(from_state, from_state)
        to_label   = STATE_LABELS_TH.get(to_state, to_state)
        allowed_labels = [STATE_LABELS_TH.get(s, s) for s in allowed]
        raise IllegalTransition(
            f"ไม่สามารถเปลี่ยนจาก '{from_label}' → '{to_label}' ได้\n"
            f"สถานะถัดไปที่อนุญาต: {', '.join(allowed_labels) or '— (สถานะ terminal)'}"
        )


def infer_state_from_data(has_tqf3_clos: bool, has_tqf5: bool) -> str:
    """
    Heuristic: derive an appropriate state from existing document data.
    Used when a new offering_status row must be created retroactively.
    """
    if has_tqf5:
        return TQF5_GENERATED
    if has_tqf3_clos:
        return TQF3_GENERATED
    return NOT_STARTED
