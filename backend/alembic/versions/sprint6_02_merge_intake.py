"""Join the simulation and patient-intake branches."""
from typing import Sequence, Union

revision: str = "sprint6_02_merge_intake"
down_revision: Union[str, Sequence[str], None] = ("sprint5_02_patient_intake", "sprint6_01_simulation")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
