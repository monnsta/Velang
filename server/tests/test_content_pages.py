from types import SimpleNamespace

from app.features.content.service import page_content_fields


def test_builtin_markdown_page_fields_use_dictionary_values():
	title, body = page_content_fields(
		{"title": "Support", "body_markdown": "Contact support."}, "support"
	)
	assert title == "Support"
	assert body == "Contact support."


def test_missing_markdown_page_fields_get_safe_defaults():
	assert page_content_fields({"body_markdown": None}, "shipping") == ("Shipping", "")


def test_legacy_database_page_fields_use_model_attributes():
	row = SimpleNamespace(title="Returns", body_markdown="Return details.")
	assert page_content_fields(row, "ignored") == ("Returns", "Return details.")
