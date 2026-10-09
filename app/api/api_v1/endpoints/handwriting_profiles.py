import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app import actions, models
from app.api import deps
from app.core.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/pjpeg", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _build_image_url(file_path: str) -> str | None:
    filename = Path(file_path).name
    base_url = getattr(settings, "STORAGE_BASE_URL", "/uploads") or "/uploads"
    return f"{base_url.rstrip('/')}/samples/{filename}"


def _get_profile_or_404(profile_id: int, db: Session) -> models.HandwritingProfile:
    profile = actions.handwriting_profile_action.get(session=db, id=profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handwriting profile not found",
        )
    return profile


@router.post(
    "/",
    response_model=models.HandwritingProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def create_handwriting_profile(
    profile_in: models.HandwritingProfileCreate,
    db: Session = Depends(deps.get_session),
) -> models.HandwritingProfile:
    """
    Create a new handwriting profile.
    """
    return actions.handwriting_profile_action.create(session=db, data=profile_in)


@router.get(
    "/",
    response_model=list[models.HandwritingProfileRead],
)
def list_handwriting_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_session),
) -> list[models.HandwritingProfile]:
    """
    Retrieve handwriting profiles.
    """
    return actions.handwriting_profile_action.get_multi(
        session=db, offset=skip, limit=limit
    )


@router.get(
    "/{profile_id}",
    response_model=models.HandwritingProfileRead,
)
def get_handwriting_profile(
    profile_id: int,
    db: Session = Depends(deps.get_session),
) -> models.HandwritingProfile:
    """
    Get a specific handwriting profile by ID.
    """
    return _get_profile_or_404(profile_id, db)


@router.put(
    "/{profile_id}",
    response_model=models.HandwritingProfileRead,
)
def update_handwriting_profile(
    profile_id: int,
    profile_in: models.HandwritingProfileUpdate,
    db: Session = Depends(deps.get_session),
) -> models.HandwritingProfile:
    """
    Update a handwriting profile.
    """
    profile = _get_profile_or_404(profile_id, db)
    return actions.handwriting_profile_action.update(
        session=db, model=profile, data=profile_in
    )


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_handwriting_profile(
    profile_id: int,
    db: Session = Depends(deps.get_session),
) -> None:
    """
    Delete a handwriting profile and clean up associated samples and disk files.
    """
    profile = _get_profile_or_404(profile_id, db)

    # Find and delete associated character sample files
    statement = select(models.CharacterSample).where(
        models.CharacterSample.profile_id == profile_id
    )
    samples = db.exec(statement).all()
    for sample in samples:
        if sample.file_path and os.path.exists(sample.file_path):
            try:
                os.remove(sample.file_path)
            except OSError:
                pass
        actions.character_sample_action.delete(session=db, id=sample.id)

    # Disassociate documents
    doc_statement = select(models.Document).where(
        models.Document.profile_id == profile_id
    )
    documents = db.exec(doc_statement).all()
    for doc in documents:
        doc.profile_id = None
        db.add(doc)
    db.commit()

    actions.handwriting_profile_action.delete(session=db, id=profile_id)


# --- Character Sample Endpoints ---



@router.post(
    "/{profile_id}/samples",
    response_model=models.CharacterSampleRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_character_sample(
    profile_id: int,
    character: str = Form(...),
    sample_type: str = Form("image"),
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_session),
) -> models.CharacterSampleRead:
    """
    Upload a character sample image for a handwriting profile.
    """
    _get_profile_or_404(profile_id, db)

    # Validate character
    character = character.strip()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character parameter cannot be empty",
        )

    # Validate file extension and MIME type
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS or (file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only image files (PNG, JPEG, WEBP, GIF) are allowed.",
        )

    # Read content & validate file size
    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 5MB",
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Prepare storage directory
    base_storage = Path(settings.STORAGE_PATH or "./uploads")
    samples_dir = base_storage / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_filename = f"sample_{uuid.uuid4().hex}{ext}"
    target_path = samples_dir / unique_filename

    with open(target_path, "wb") as f:
        f.write(contents)

    file_path_str = str(target_path)
    sample_in = models.CharacterSampleCreate(
        profile_id=profile_id,
        character=character,
        sample_type=sample_type,
        file_path=file_path_str,
    )
    sample = actions.character_sample_action.create(session=db, data=sample_in)

    res = models.CharacterSampleRead.model_validate(sample)
    res.image_url = _build_image_url(file_path_str)
    return res


@router.get(
    "/{profile_id}/samples",
    response_model=list[models.CharacterSampleRead],
)
def list_character_samples(
    profile_id: int,
    db: Session = Depends(deps.get_session),
) -> list[models.CharacterSampleRead]:
    """
    List character samples for a given handwriting profile.
    """
    _get_profile_or_404(profile_id, db)

    statement = select(models.CharacterSample).where(
        models.CharacterSample.profile_id == profile_id
    )
    samples = db.exec(statement).all()

    result = []
    for s in samples:
        read_obj = models.CharacterSampleRead.model_validate(s)
        read_obj.image_url = _build_image_url(s.file_path)
        result.append(read_obj)
    return result


@router.get(
    "/{profile_id}/samples/{sample_id}",
    response_model=models.CharacterSampleRead,
)
def get_character_sample(
    profile_id: int,
    sample_id: int,
    db: Session = Depends(deps.get_session),
) -> models.CharacterSampleRead:
    """
    Retrieve metadata for a specific character sample.
    """
    _get_profile_or_404(profile_id, db)

    sample = actions.character_sample_action.get(session=db, id=sample_id)
    if not sample or sample.profile_id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character sample not found",
        )

    read_obj = models.CharacterSampleRead.model_validate(sample)
    read_obj.image_url = _build_image_url(sample.file_path)
    return read_obj


@router.delete(
    "/{profile_id}/samples/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_character_sample(
    profile_id: int,
    sample_id: int,
    db: Session = Depends(deps.get_session),
) -> None:
    """
    Delete a character sample and its stored file.
    """
    _get_profile_or_404(profile_id, db)

    sample = actions.character_sample_action.get(session=db, id=sample_id)
    if not sample or sample.profile_id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character sample not found",
        )

    # Safely remove file on disk
    if sample.file_path and os.path.exists(sample.file_path):
        try:
            os.remove(sample.file_path)
        except OSError:
            pass

    actions.character_sample_action.delete(session=db, id=sample_id)
