from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class HandwritingProfileBase(SQLModel):
    profile_name: str = Field(min_length=1, index=True)
    description: str | None = None


class HandwritingProfile(HandwritingProfileBase, table=True):
    __tablename__ = "handwritingprofile"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HandwritingProfileCreate(HandwritingProfileBase):
    pass


class HandwritingProfileRead(HandwritingProfileBase):
    id: int
    created_at: datetime


class HandwritingProfileUpdate(SQLModel):
    profile_name: str | None = None
    description: str | None = None
