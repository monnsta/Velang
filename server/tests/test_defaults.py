from app.core.site_defaults import DEFAULT_SITE


def test_default_site_has_required_light_only_storefront_controls():
	"""Verify defaults match the category-led, light-only storefront."""
	assert DEFAULT_SITE["site"]["name"]
	assert DEFAULT_SITE["theme"]["mode"] == "light"
	assert "dark" not in DEFAULT_SITE["theme"]
	assert DEFAULT_SITE["theme"]["light"]["background"].startswith("#")
	assert DEFAULT_SITE["navigation"] == []
	assert DEFAULT_SITE["homepage"] == []
	assert all(item["href"].startswith("/") for item in DEFAULT_SITE["footer"])
