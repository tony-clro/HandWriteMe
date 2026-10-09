from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class CharacterSampleBase(SQLModel):
    character: str = Field(min_length=1, max_length=10, index=True)
    sample_type: str = Field(default="image")
    file_path: str


class CharacterSample(CharacterSampleBase, table=True):
    __tablename__ = "charactersample"

    id: int | None = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="handwritingprofile.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CharacterSampleCreate(CharacterSampleBase):
    profile_id: int


class CharacterSampleRead(CharacterSampleBase):
    id: int
    profile_id: int
    image_url: str | None = None
    created_at: datetime


class CharacterSampleUpdate(SQLModel):
    character: str | None = None
    sample_type: str | None = None
    file_path: str | None = None
