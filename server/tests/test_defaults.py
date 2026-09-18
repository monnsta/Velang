from app.core.site_defaults import DEFAULT_SITE


def test_default_site_has_required_storefront_controls():
	assert DEFAULT_SITE["site"]["name"]
	assert DEFAULT_SITE["theme"]["background"].startswith("#")
	assert DEFAULT_SITE["navigation"]
	assert DEFAULT_SITE["homepage"]
	assert any(block["type"] == "hero" for block in DEFAULT_SITE["homepage"])
