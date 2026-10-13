from copy import deepcopy

from app.core.site import _merge
from app.core.site_defaults import DEFAULT_SITE


def test_theme_is_light_only():
	"""Only the light palette is part of the supported storefront theme."""
	theme = DEFAULT_SITE["theme"]
	assert theme["mode"] == "light"
	assert "dark" not in theme


def test_site_merge_preserves_new_defaults_when_old_database_is_missing_fields():
	old = {
		"mode": "system",
		"dark": {"background": "#000"},
		"light": {"background": "#fff"},
	}
	merged = _merge(deepcopy(DEFAULT_SITE["theme"]), old)
	assert merged["light"]["background"] == "#fff"
	assert merged["light"]["text"]
	# Legacy database keys may still exist until saved, but they are not rendered.


def test_homepage_has_no_configured_featured_or_collection_sections():
	assert DEFAULT_SITE["homepage"] == []
