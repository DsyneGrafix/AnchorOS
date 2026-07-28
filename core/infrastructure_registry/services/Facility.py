@dataclass
class Facility:
    id: UUID
    external_id: str | None
    name: str
    organization_id: UUID
    lifecycle_state: LifecycleState
    created_at: datetime
    updated_at: datetime
