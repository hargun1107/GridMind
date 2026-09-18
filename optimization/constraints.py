"""Mathematical Optimization Constraints Specifications.

Defines the mathematical formulations for:
- Max transformer/feeder capacity limits
- Appliance run durations and continuity
- User-specified completion deadlines
- Non-flexible baseload guarantees
"""

from typing import NamedTuple


class ApplianceConstraint(NamedTuple):
    name: str
    rated_kw: float
    required_minutes: int
    flexible: bool
    latest_finish_time: str
