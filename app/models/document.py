from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class DocumentBase(SQLModel):
    filename: str = Field(index=True)
    file_size: int
    status: str = Field(default="completed")
    page_count: int = Field(default=0)
    profile_id: int | None = Field(default=None, foreign_key="handwritingprofile.id", nullable=True, index=True)


class Document(DocumentBase, table=True):
    __tablename__ = "document"

    id: int | None = Field(default=None, primary_key=True)
    stored_filename: str
    file_path: str
    extracted_text: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentCreate(DocumentBase):
    stored_filename: str
    file_path: str
    extracted_text: str | None = None


class DocumentRead(DocumentBase):
    id: int
    stored_filename: str
    created_at: datetime


class DocumentDetailRead(DocumentRead):
    extracted_text: str | None = None


class DocumentTextResponse(SQLModel):
    id: int
    status: str
    page_count: int
    extracted_text: str | None = None


class DocumentUpdate(SQLModel):
    status: str | None = None
    extracted_text: str | None = None
