from pathlib import Path

from app.core.enums import DocumentCategory
from app.retrieval.chunking import document_id_from_path
from app.retrieval.ingest import category_for_stem
from app.retrieval.unstructured_parser import list_knowledge_files


def test_knowledge_dir_has_enterprise_scale_corpus() -> None:
    files = list_knowledge_files(Path("knowledge"))
    assert len(files) >= 30
    assert {path.suffix.lower() for path in files} <= {
        ".md",
        ".pdf",
        ".docx",
        ".pptx",
        ".html",
        ".htm",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".tiff",
        ".tif",
    }


def test_category_prefix_does_not_confuse_installment_with_install() -> None:
    assert category_for_stem("installment_huabei") == DocumentCategory.PAYMENT
    assert category_for_stem("install_appliance") == DocumentCategory.PRODUCT
    assert category_for_stem("return_policy") == DocumentCategory.RETURN_POLICY
    assert category_for_stem("coupons") == DocumentCategory.COUPON
    assert category_for_stem("privacy_cs") == DocumentCategory.ACCOUNT
    assert category_for_stem("unknown_topic") == DocumentCategory.FAQ


def test_document_id_is_independent_of_checkout_location(tmp_path: Path) -> None:
    first = tmp_path / "checkout-a" / "knowledge"
    second = tmp_path / "checkout-b" / "knowledge"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    assert document_id_from_path(first / "return_policy.md", root=first) == document_id_from_path(
        second / "return_policy.md", root=second
    )
