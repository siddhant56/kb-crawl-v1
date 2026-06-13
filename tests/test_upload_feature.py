"""
tests/test_upload_feature.py
----------------------------
Comprehensive tests for the document upload feature.

Sections
--------
1. Sanitizer — unit tests for each pattern category and edge cases
2. SanitizationReport — dataclass behaviour
3. Upload router — integration tests via FastAPI TestClient (mocked deps)
4. Admin grant/revoke-upload endpoints
5. require_upload_access dependency
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_module.database import get_db
from auth_module.dependencies import require_upload_access
from auth_module.models import Base, User, UserRole, UserStatus
from auth_module.routers.admin import router as admin_router
from auth_module.routers.upload import router as upload_router
from auth_module.sanitizer import SanitizationReport, is_clean, sanitize

# Pre-import so the module is cached before we patch it in tests
import pro_implementation.ingest  # noqa: F401


# ─── Shared DB helpers ────────────────────────────────────────────────────────

def _make_test_engine():
    # StaticPool ensures all sessions share the same in-memory SQLite connection
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _make_session_factory(engine):
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — Sanitizer unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSanitizerApiKeys:

    def test_openai_sk_key_redacted(self):
        text = "Our API key is sk-proj-abc1234567890abcdefghijklm and nothing else."
        clean, report = sanitize(text)
        assert "[REDACTED:API_KEY]" in clean
        assert "sk-proj-abc1234567890abcdefghijklm" not in clean
        assert report.total >= 1
        assert "API_KEY" in report.by_category

    def test_openai_sk_short_prefix_redacted(self):
        text = "key=sk-abcdefghijklmnopqrstuvwxyz12345678"
        clean, report = sanitize(text)
        assert "API_KEY" in report.by_category or "SECRET" in report.by_category

    def test_aws_access_key_id_redacted(self):
        text = "AKIAIOSFODNN7EXAMPLE is the key."
        clean, report = sanitize(text)
        assert "[REDACTED:API_KEY]" in clean
        assert "AKIAIOSFODNN7EXAMPLE" not in clean

    def test_google_api_key_redacted(self):
        text = "key = AIzaSyDm1234567890abcdefghijklmnopqrstu"
        clean, report = sanitize(text)
        assert "API_KEY" in report.by_category
        assert "AIzaSy" not in clean

    def test_github_token_redacted(self):
        # Pattern requires 36+ chars after prefix — use full-length token
        text = "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234567890abcdefghij"
        clean, report = sanitize(text)
        assert "API_KEY" in report.by_category

    def test_stripe_live_key_redacted(self):
        # Construct the key string dynamically to avoid triggering secret scanners
        fake_key = "sk_" + "live" + "_" + "a" * 28
        text = f"stripe_key={fake_key}"
        clean, report = sanitize(text)
        assert "API_KEY" in report.by_category

    def test_jwt_token_redacted(self):
        # Three-part JWT (header.payload.signature) matches TOKEN pattern
        text = "token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        clean, report = sanitize(text)
        assert "TOKEN" in report.by_category

    def test_bearer_authorization_header_redacted(self):
        # Pattern matches "Authorization=<token>" or "Bearer=<token>" format
        text = "Authorization=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.SflKxwRJSMeKKF2QT4"
        clean, report = sanitize(text)
        assert "TOKEN" in report.by_category or "SECRET" in report.by_category


class TestSanitizerCredentials:

    def test_password_assignment_redacted(self):
        text = "password=SuperSecret99!"
        clean, report = sanitize(text)
        assert "[REDACTED:PASSWORD]" in clean
        assert "SuperSecret99!" not in clean
        assert "PASSWORD" in report.by_category

    def test_passwd_variant_redacted(self):
        text = "passwd: hunter2abc"
        clean, report = sanitize(text)
        assert "PASSWORD" in report.by_category

    def test_postgresql_dsn_redacted(self):
        text = "DATABASE_URL=postgresql://user:s3cr3t@db.host:5432/mydb"
        clean, report = sanitize(text)
        assert "CREDENTIAL" in report.by_category
        assert "s3cr3t" not in clean

    def test_mongodb_dsn_redacted(self):
        text = "db=mongodb://admin:password123@cluster0.mongodb.net/mydb"
        clean, report = sanitize(text)
        assert "CREDENTIAL" in report.by_category

    def test_pem_private_key_redacted(self):
        text = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890\n"
            "-----END RSA PRIVATE KEY-----"
        )
        clean, report = sanitize(text)
        assert "PRIVATE_KEY" in report.by_category
        assert "MIIEpAIBAAKCAQEA1234567890" not in clean

    def test_api_key_value_secret_redacted(self):
        text = "api_key=mysupersecretvalue123"
        clean, report = sanitize(text)
        assert "SECRET" in report.by_category


class TestSanitizerPricing:

    def test_labeled_price_line_redacted(self):
        text = "pricing: $99/month for the starter plan"
        clean, report = sanitize(text)
        assert "PRICING" in report.by_category

    def test_per_unit_currency_redacted(self):
        text = "costs $299/user billed annually"
        clean, report = sanitize(text)
        assert "PRICING" in report.by_category

    def test_bare_dollar_sign_not_redacted(self):
        """$N without a pricing label or per-unit suffix must not be redacted."""
        text = "Step $1 is to install the package. Move to $2 and configure."
        clean, report = sanitize(text)
        assert "PRICING" not in report.by_category

    def test_promo_code_redacted(self):
        text = "promo code: SAVE20"
        clean, report = sanitize(text)
        assert "PRICING" in report.by_category

    def test_cost_equals_redacted(self):
        text = "cost = $49.99/mo per seat"
        clean, report = sanitize(text)
        assert "PRICING" in report.by_category


class TestSanitizerPII:

    def test_email_redacted(self):
        text = "Contact us at ceo@bigcorp.com for a demo."
        clean, report = sanitize(text)
        assert "[REDACTED:PII_EMAIL]" in clean
        assert "ceo@bigcorp.com" not in clean
        assert "PII_EMAIL" in report.by_category

    def test_us_phone_number_redacted(self):
        text = "Call us at (415) 555-0100 or +1-800-555-1234."
        clean, report = sanitize(text)
        assert "PII_PHONE" in report.by_category

    def test_ssn_redacted(self):
        text = "SSN: 123-45-6789"
        clean, report = sanitize(text)
        assert "PII_SSN" in report.by_category
        assert "123-45-6789" not in clean

    def test_credit_card_redacted(self):
        text = "Card: 4111 1111 1111 1111"
        clean, report = sanitize(text)
        assert "PII_CARD" in report.by_category


class TestSanitizerClientInfo:

    def test_client_labeled_line_redacted(self):
        text = "Client: Acme Corporation"
        clean, report = sanitize(text)
        assert "CLIENT_INFO" in report.by_category

    def test_customer_name_redacted(self):
        text = "Customer Name: John Smith"
        clean, report = sanitize(text)
        assert "CLIENT_INFO" in report.by_category

    def test_invoice_number_redacted(self):
        text = "Invoice #: INV-2024-001"
        clean, report = sanitize(text)
        assert "CLIENT_INFO" in report.by_category


class TestSanitizerFalsePositives:

    def test_generic_hex_sha256_not_redacted(self):
        """SHA-256 file hash in a normal sentence must not trigger SECRET."""
        text = (
            "The file checksum is a3f8d2c1e5b7a9f0c2d4e6b8f1a3d5e7b9c1e3f5a7b9d1e3f5a7b9d1e3f5a7b9. "
            "Please verify before installing."
        )
        clean, report = sanitize(text)
        # Should not redact standalone hex strings without context
        assert "SECRET" not in report.by_category

    def test_normal_prose_untouched(self):
        text = (
            "Radixweb is a leading software development company. "
            "We deliver custom solutions for enterprise clients worldwide. "
            "Our team has over 500 developers with expertise in AI, cloud, and mobile."
        )
        clean, report = sanitize(text)
        assert report.total == 0
        assert clean == text

    def test_empty_string_untouched(self):
        clean, report = sanitize("")
        assert clean == ""
        assert report.total == 0

    def test_is_clean_returns_true_for_safe_text(self):
        assert is_clean("Hello, world! This is a perfectly safe document.") is True

    def test_is_clean_returns_false_for_sensitive_text(self):
        assert is_clean("password=SuperSecret99!") is False


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — SanitizationReport dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSanitizationReport:

    def test_total_zero_on_empty_report(self):
        r = SanitizationReport()
        assert r.total == 0

    def test_total_reflects_redaction_count(self):
        r = SanitizationReport(redactions=[
            {"category": "API_KEY", "original_snippet": "sk-xxx", "position": 0},
            {"category": "PII_EMAIL", "original_snippet": "a@b.com", "position": 50},
        ])
        assert r.total == 2

    def test_by_category_counts_correctly(self):
        r = SanitizationReport(redactions=[
            {"category": "API_KEY", "original_snippet": "sk-xxx", "position": 0},
            {"category": "API_KEY", "original_snippet": "sk-yyy", "position": 10},
            {"category": "PII_EMAIL", "original_snippet": "a@b.com", "position": 50},
        ])
        assert r.by_category == {"API_KEY": 2, "PII_EMAIL": 1}

    def test_str_no_redactions(self):
        r = SanitizationReport()
        assert str(r) == "No sensitive data found."

    def test_str_with_redactions_shows_counts(self):
        r = SanitizationReport(redactions=[
            {"category": "PASSWORD", "original_snippet": "hunter2", "position": 0},
            {"category": "PASSWORD", "original_snippet": "abc123", "position": 30},
            {"category": "PII_EMAIL", "original_snippet": "x@y.com", "position": 60},
        ])
        output = str(r)
        assert "Redacted 3 items" in output
        assert "PASSWORD: 2" in output
        assert "PII_EMAIL: 1" in output

    def test_sanitize_returns_position_metadata(self):
        text = "Some preamble. password=s3cr3t. More text."
        _, report = sanitize(text)
        password_redactions = [r for r in report.redactions if r["category"] == "PASSWORD"]
        assert len(password_redactions) >= 1
        for r in password_redactions:
            assert isinstance(r["position"], int)
            assert 0 <= r["position"] < len(text)

    def test_multiple_categories_all_accounted_for(self):
        text = (
            "Contact: ceo@bigcorp.com\n"
            "API Key: sk-fakeapikey1234567890abcdefghij\n"
            "rate: $999/mo\n"
        )
        _, report = sanitize(text)
        categories = set(report.by_category.keys())
        assert "PII_EMAIL" in categories
        assert "API_KEY" in categories
        assert "PRICING" in categories


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Upload router integration tests
# ═══════════════════════════════════════════════════════════════════════════════

FAKE_USER = MagicMock(spec=User)
FAKE_USER.id = 1
FAKE_USER.email = "uploader@example.com"
FAKE_USER.role = UserRole.USER
FAKE_USER.status = UserStatus.APPROVED
FAKE_USER.upload_access = True


def _build_upload_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(upload_router)
    app.dependency_overrides[require_upload_access] = lambda: FAKE_USER

    import auth_module.routers.upload as upload_mod
    upload_mod.KNOWLEDGE_BASE_PATH = tmp_path

    return app


@pytest.fixture()
def upload_client(tmp_path):
    app = _build_upload_app(tmp_path)
    # Patch at the source module so the local import inside the route handler picks it up
    with patch(
        "pro_implementation.ingest.append_document",
        return_value={"chunks_added": 5, "chunks_removed": 0},
    ):
        yield TestClient(app)


def _txt_upload(content: str = None, filename: str = "test.txt", category: str = "uploads"):
    body = content or ("A" * 200)
    return {
        "file": (filename, io.BytesIO(body.encode()), "text/plain"),
        "category": (None, category),
    }


class TestUploadValidCategory:

    def test_all_valid_categories_accepted(self, tmp_path):
        from auth_module.routers.upload import VALID_CATEGORIES
        app = _build_upload_app(tmp_path)
        with patch(
            "pro_implementation.ingest.append_document",
            return_value={"chunks_added": 2, "chunks_removed": 0},
        ):
            client = TestClient(app)
            for cat in VALID_CATEGORIES:
                resp = client.post("/api/upload", files=_txt_upload(category=cat))
                assert resp.status_code == 200, f"Category '{cat}' unexpectedly rejected: {resp.text}"

    def test_invalid_category_returns_422(self, upload_client):
        files = _txt_upload(category="totally-invalid-category")
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 422
        assert "Invalid category" in resp.json()["detail"]


class TestUploadFileTypes:

    def test_txt_upload_succeeds(self, upload_client):
        content = "This is a valid plain text document. " * 10
        files = _txt_upload(content=content)
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["category"] == "uploads"
        assert body["filename"] == "test.txt"
        assert "chunks_added" in body
        assert "sanitization" in body
        assert body["uploaded_by"] == "uploader@example.com"

    def test_md_upload_succeeds(self, upload_client):
        content = "# My Doc\n\n" + "Some markdown content here. " * 10
        files = {
            "file": ("doc.md", io.BytesIO(content.encode()), "text/markdown"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 200
        assert resp.json()["filename"] == "doc.md"

    def test_pdf_upload_succeeds(self, upload_client):
        with patch("auth_module.routers.upload._pdf_to_text", return_value="A" * 200):
            with patch("pro_implementation.ingest.append_document", return_value={"chunks_added": 4, "chunks_removed": 0}):
                resp = upload_client.post(
                    "/api/upload",
                    files={
                        "file": ("report.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf"),
                        "category": (None, "uploads"),
                    },
                )
        assert resp.status_code == 200
        assert resp.json()["filename"] == "report.pdf"

    def test_docx_upload_succeeds(self, upload_client):
        with patch("auth_module.routers.upload._docx_to_text", return_value="B" * 200):
            with patch("pro_implementation.ingest.append_document", return_value={"chunks_added": 6, "chunks_removed": 0}):
                resp = upload_client.post(
                    "/api/upload",
                    files={
                        "file": ("spec.docx", io.BytesIO(b"PK fake docx"), "application/vnd.openxmlformats"),
                        "category": (None, "blog"),
                    },
                )
        assert resp.status_code == 200

    def test_unsupported_extension_returns_415(self, upload_client):
        files = {
            "file": ("image.png", io.BytesIO(b"\x89PNG\r\n"), "image/png"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 415
        assert "Unsupported file type" in resp.json()["detail"]

    def test_exe_extension_returns_415(self, upload_client):
        files = {
            "file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 415


class TestUploadSizeChecks:

    def test_empty_file_returns_422(self, upload_client):
        files = {
            "file": ("empty.txt", io.BytesIO(b""), "text/plain"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()

    def test_file_too_large_returns_413(self, upload_client):
        big_data = b"X" * (51 * 1024 * 1024)
        files = {
            "file": ("huge.txt", io.BytesIO(big_data), "text/plain"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 413
        assert "50 MB" in resp.json()["detail"]


class TestUploadExtractedTextLength:

    def test_file_with_too_short_extracted_text_returns_422(self, upload_client):
        files = {
            "file": ("tiny.txt", io.BytesIO(b"Hi."), "text/plain"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 422
        assert "too short" in resp.json()["detail"].lower()

    def test_file_with_exactly_49_chars_returns_422(self, upload_client):
        content = "A" * 49
        files = {
            "file": ("borderline.txt", io.BytesIO(content.encode()), "text/plain"),
            "category": (None, "uploads"),
        }
        resp = upload_client.post("/api/upload", files=files)
        assert resp.status_code == 422

    def test_file_with_exactly_50_chars_accepted(self, upload_client):
        content = "A" * 50
        resp = upload_client.post(
            "/api/upload",
            files={
                "file": ("ok.txt", io.BytesIO(content.encode()), "text/plain"),
                "category": (None, "uploads"),
            },
        )
        assert resp.status_code == 200


class TestUploadSanitization:

    def test_response_includes_redaction_count_for_sensitive_doc(self, upload_client):
        content = (
            "Contact: ceo@secret-corp.com\n"
            "API key: sk-fakeapikey1234567890abcdefghij\n"
            "More text. " * 10
        )
        resp = upload_client.post(
            "/api/upload",
            files={
                "file": ("sensitive.txt", io.BytesIO(content.encode()), "text/plain"),
                "category": (None, "uploads"),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sanitization"]["redactions_total"] >= 1

    def test_clean_document_has_zero_redactions(self, upload_client):
        content = (
            "Our company offers custom software development services. "
            "We deliver enterprise solutions across web, mobile, and cloud. " * 5
        )
        resp = upload_client.post(
            "/api/upload",
            files={
                "file": ("clean.txt", io.BytesIO(content.encode()), "text/plain"),
                "category": (None, "services"),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["sanitization"]["redactions_total"] == 0


class TestUploadSavedFile:

    def test_saved_md_file_exists_in_category_dir(self, upload_client, tmp_path):
        content = "This is a test document. " * 20
        resp = upload_client.post(
            "/api/upload",
            files=_txt_upload(content=content, filename="myreport.txt", category="blog"),
        )
        assert resp.status_code == 200
        saved_as = resp.json()["saved_as"]
        saved_path = tmp_path / "blog" / saved_as
        assert saved_path.exists(), f"Expected {saved_path} to exist"

    def test_saved_file_has_user_prefix(self, upload_client, tmp_path):
        content = "A" * 200
        resp = upload_client.post(
            "/api/upload",
            files=_txt_upload(content=content, filename="doc.txt"),
        )
        assert resp.status_code == 200
        assert resp.json()["saved_as"].startswith("user-")

    def test_saved_file_rolled_back_on_embed_failure(self, tmp_path):
        app = _build_upload_app(tmp_path)
        with patch(
            "pro_implementation.ingest.append_document",
            side_effect=RuntimeError("ChromaDB unavailable"),
        ):
            client = TestClient(app)
            resp = client.post(
                "/api/upload",
                files=_txt_upload(content="A" * 200, filename="fail.txt"),
            )
        assert resp.status_code == 500
        assert "Embedding failed" in resp.json()["detail"]
        uploads_dir = tmp_path / "uploads"
        if uploads_dir.exists():
            md_files = list(uploads_dir.glob("*.md"))
            assert md_files == [], f"Orphaned files found: {md_files}"

    def test_title_override_used_as_document_heading(self, upload_client, tmp_path):
        content = "Some content here. " * 15
        resp = upload_client.post(
            "/api/upload",
            files={
                "file": ("original.txt", io.BytesIO(content.encode()), "text/plain"),
                "category": (None, "uploads"),
                "title": (None, "My Custom Title"),
            },
        )
        assert resp.status_code == 200
        saved_as = resp.json()["saved_as"]
        saved_path = tmp_path / "uploads" / saved_as
        saved_content = saved_path.read_text()
        assert "# My Custom Title" in saved_content

    def test_title_with_newlines_is_collapsed(self, upload_client, tmp_path):
        content = "A" * 200
        resp = upload_client.post(
            "/api/upload",
            files={
                "file": ("test.txt", io.BytesIO(content.encode()), "text/plain"),
                "category": (None, "uploads"),
                "title": (None, "Line One\nLine Two"),
            },
        )
        assert resp.status_code == 200
        saved_as = resp.json()["saved_as"]
        saved_content = (tmp_path / "uploads" / saved_as).read_text()
        # Newline should have been collapsed to a space
        assert "# Line One Line Two" in saved_content


class TestUploadGetCategories:

    def test_categories_endpoint_returns_list(self, upload_client):
        resp = upload_client.get("/api/upload/categories")
        assert resp.status_code == 200
        body = resp.json()
        assert "categories" in body
        assert isinstance(body["categories"], list)
        assert "uploads" in body["categories"]
        assert "blog" in body["categories"]

    def test_categories_endpoint_requires_no_auth(self, tmp_path):
        app = FastAPI()
        app.include_router(upload_router)
        # No dependency overrides — GET /categories has no auth
        import auth_module.routers.upload as upload_mod
        upload_mod.KNOWLEDGE_BASE_PATH = tmp_path
        client = TestClient(app)
        resp = client.get("/api/upload/categories")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Admin grant/revoke-upload endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def db_session():
    engine = _make_test_engine()
    factory = _make_session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _make_user(
    db,
    email: str,
    role: UserRole = UserRole.USER,
    status: UserStatus = UserStatus.APPROVED,
    upload_access: bool = False,
) -> User:
    import bcrypt
    hashed = bcrypt.hashpw(b"Test1234!", bcrypt.gensalt()).decode()
    user = User(
        email=email,
        full_name="Test User",
        hashed_password=hashed,
        role=role,
        status=status,
        upload_access=upload_access,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _build_admin_app(db_session) -> FastAPI:
    from auth_module.dependencies import require_super_admin

    app = FastAPI()
    app.include_router(admin_router)

    admin_user = MagicMock(spec=User)
    admin_user.id = 9999
    admin_user.role = UserRole.SUPER_ADMIN
    admin_user.status = UserStatus.APPROVED

    app.dependency_overrides[require_super_admin] = lambda: admin_user

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    return app


class TestGrantUploadAccess:

    def test_grant_upload_to_approved_user(self, db_session):
        target = _make_user(db_session, "target@example.com", upload_access=False)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/grant-upload")
        assert resp.status_code == 200
        assert resp.json()["upload_access"] is True

    def test_grant_upload_to_pending_user_fails(self, db_session):
        target = _make_user(db_session, "pending@example.com", status=UserStatus.PENDING)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/grant-upload")
        assert resp.status_code == 400
        assert "approved" in resp.json()["detail"].lower()

    def test_grant_upload_to_super_admin_fails(self, db_session):
        target = _make_user(db_session, "superadmin@example.com", role=UserRole.SUPER_ADMIN)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/grant-upload")
        assert resp.status_code == 400

    def test_grant_upload_to_nonexistent_user_returns_404(self, db_session):
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch("/auth/admin/users/99999/grant-upload")
        assert resp.status_code == 404

    def test_grant_upload_self_raises_400(self, db_session):
        from auth_module.dependencies import require_super_admin
        admin_user = _make_user(db_session, "selfadmin@example.com", role=UserRole.SUPER_ADMIN)
        app = FastAPI()
        app.include_router(admin_router)
        app.dependency_overrides[require_super_admin] = lambda: admin_user

        def _override_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_db
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{admin_user.id}/grant-upload")
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"].lower()


class TestRevokeUploadAccess:

    def test_revoke_upload_from_user_with_access(self, db_session):
        target = _make_user(db_session, "with-upload@example.com", upload_access=True)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/revoke-upload")
        assert resp.status_code == 200
        assert resp.json()["upload_access"] is False

    def test_revoke_upload_from_user_without_access_is_idempotent(self, db_session):
        target = _make_user(db_session, "no-upload@example.com", upload_access=False)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/revoke-upload")
        assert resp.status_code == 200
        assert resp.json()["upload_access"] is False

    def test_revoke_upload_from_super_admin_fails(self, db_session):
        target = _make_user(db_session, "supe2@example.com", role=UserRole.SUPER_ADMIN, upload_access=True)
        app = _build_admin_app(db_session)
        client = TestClient(app)

        resp = client.patch(f"/auth/admin/users/{target.id}/revoke-upload")
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — require_upload_access dependency
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequireUploadAccessDependency:

    def test_approved_user_with_upload_access_passes(self):
        user = MagicMock(spec=User)
        user.status = UserStatus.APPROVED
        user.upload_access = True

        from auth_module.dependencies import require_upload_access as _dep
        # Simulate calling the inner logic without the DB
        # (We test via the upload endpoint, which overrides the dep)
        # Direct unit test: patch require_approved to return the mock user
        with patch("auth_module.dependencies.require_approved", return_value=user):
            result = _dep(user=user)
        assert result is user

    def test_approved_user_without_upload_access_raises_403(self):
        user = MagicMock(spec=User)
        user.status = UserStatus.APPROVED
        user.upload_access = False

        from fastapi import HTTPException
        from auth_module.dependencies import require_upload_access as _dep

        with pytest.raises(HTTPException) as exc_info:
            _dep(user=user)
        assert exc_info.value.status_code == 403
        assert "Upload access" in exc_info.value.detail
