"""Regression coverage for built-in Markdown page discovery and visibility."""

from app.features.content.service import _parse_markdown_page, _static_page, static_pages


def test_static_markdown_frontmatter_respects_active_flag():
	active = _parse_markdown_page('---\ntitle: "Company"\nactive: true\n---\n\nHello', "company")
	inactive = _parse_markdown_page('---\ntitle: "Company"\nactive: false\n---\n\nHello', "company")

	assert active["title"] == "Company"
	assert active["active"] is True
	assert active["body_markdown"] == "Hello"
	assert inactive["active"] is False


def test_static_page_lookup_rejects_path_traversal():
	assert _static_page("../README") is None
	assert _static_page("terms/../../README") is None


def test_builtin_pages_are_discoverable_for_admin():
	pages = static_pages(include_inactive=True)
	slugs = {page["slug"] for page in pages}
	assert {"the-company", "terms", "privacy", "return-policy", "support"}.issubset(slugs)
	assert all("title" in page and "body_markdown" in page for page in pages)


def test_static_frontmatter_round_trips_quoted_titles():
	page = _parse_markdown_page('---\ntitle: "The \\"Company\\"\\\\s page"\nactive: true\n---\n\nHello', "the-company")
	assert page["title"] == 'The "Company"\\s page'
