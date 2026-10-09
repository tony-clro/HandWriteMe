import io
import os
from fastapi.testclient import TestClient

from app.core.config import settings

VALID_PDF_WITH_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 55>>stream\n"
    b"BT /F1 24 Tf 100 700 Td (Hello HandWrite Me) Tj ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n00000000101 00000 n \n0000000213 00000 n \n0000000287 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n393\n%%EOF\n"
)

BLANK_PDF_NO_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n165\n%%EOF\n"
)


def test_upload_pdf_success(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("sample.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample.pdf"
    assert data["file_size"] == len(VALID_PDF_WITH_TEXT)
    assert data["status"] == "completed"
    assert data["page_count"] == 1
    assert "stored_filename" in data


def test_extract_text_from_pdf(client: TestClient) -> None:
    upload_res = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("text_sample.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    ).json()

    doc_id = upload_res["id"]

    # Detail GET
    detail_res = client.get(f"{settings.API_V1_STR}/documents/{doc_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["extracted_text"] == "Hello HandWrite Me"

    # Text endpoint GET
    text_res = client.get(f"{settings.API_V1_STR}/documents/{doc_id}/text")
    assert text_res.status_code == 200
    t_data = text_res.json()
    assert t_data["id"] == doc_id
    assert t_data["status"] == "completed"
    assert t_data["page_count"] == 1
    assert t_data["extracted_text"] == "Hello HandWrite Me"


def test_list_documents(client: TestClient) -> None:
    client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("doc1.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    )
    client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("doc2.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    )

    response = client.get(f"{settings.API_V1_STR}/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) >= 2
    for doc in docs:
        assert "id" in doc
        assert "filename" in doc
        assert "extracted_text" not in doc  # List endpoint does not return full extracted_text


def test_get_document_by_id(client: TestClient) -> None:
    doc = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("single.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    ).json()

    doc_id = doc["id"]
    response = client.get(f"{settings.API_V1_STR}/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["id"] == doc_id
    assert response.json()["filename"] == "single.pdf"


def test_get_document_text_by_id(client: TestClient) -> None:
    doc = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("text_doc.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    ).json()

    doc_id = doc["id"]
    response = client.get(f"{settings.API_V1_STR}/documents/{doc_id}/text")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["extracted_text"] == "Hello HandWrite Me"


def test_upload_invalid_file(client: TestClient) -> None:
    invalid_content = b"This is plain text, not a PDF document"
    response = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("notes.txt", io.BytesIO(invalid_content), "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"] or "Invalid or corrupted PDF" in response.json()["detail"]


def test_upload_empty_file(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]


def test_upload_file_exceeding_size_limit(client: TestClient) -> None:
    large_file = b"%PDF-1.4 " + b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("large.pdf", io.BytesIO(large_file), "application/pdf")},
    )
    assert response.status_code == 400
    assert "File size exceeds maximum" in response.json()["detail"]


def test_get_nonexistent_document_404(client: TestClient) -> None:
    res1 = client.get(f"{settings.API_V1_STR}/documents/999999")
    assert res1.status_code == 404
    assert res1.json()["detail"] == "Document not found"

    res2 = client.get(f"{settings.API_V1_STR}/documents/999999/text")
    assert res2.status_code == 404
    assert res2.json()["detail"] == "Document not found"


def test_pdf_with_no_extractable_text(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("blank.pdf", io.BytesIO(BLANK_PDF_NO_TEXT), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "no_text"
    assert data["page_count"] == 1

    text_res = client.get(f"{settings.API_V1_STR}/documents/{data['id']}/text")
    assert text_res.status_code == 200
    assert text_res.json()["extracted_text"] == ""


def test_document_database_record_creation(client: TestClient) -> None:
    res = client.post(
        f"{settings.API_V1_STR}/documents",
        files={"file": ("db_test.pdf", io.BytesIO(VALID_PDF_WITH_TEXT), "application/pdf")},
    )
    assert res.status_code == 201
    doc = res.json()
    assert doc["filename"] == "db_test.pdf"
    assert doc["file_size"] == len(VALID_PDF_WITH_TEXT)
    assert doc["status"] == "completed"
