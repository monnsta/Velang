from app.core.site_defaults import DEFAULT_SITE


def test_storefront_uses_category_navigation_without_collections():
	"""Navigation is category-driven; no generic shop or collection menu is seeded."""
	assert DEFAULT_SITE["navigation"] == []
	assert all(item["href"].startswith("/") for item in DEFAULT_SITE["footer"])


def test_homepage_does_not_seed_featured_or_collection_sections():
	assert DEFAULT_SITE["homepage"] == []
