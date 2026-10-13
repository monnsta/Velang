import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "server" / "app" / "templates"


def test_every_jinja_template_reference_exists():
	text = "\n".join(
		path.read_text(encoding="utf-8")
		for path in (ROOT / "server" / "app").rglob("*.py")
	)
	references = set(re.findall(r"[\"\']([^\"\']+\.html)[\"\']", text))
	for reference in references:
		assert (TEMPLATES / reference).exists(), reference


def test_storefront_does_not_use_ascii_icon_glyphs():
	for path in (ROOT / "server" / "app" / "templates").rglob("*.html"):
		text = path.read_text(encoding="utf-8")
		assert not re.search(r"[☰⌕◰◎♡♥↻]", text), path


def test_media_directory_contains_seed_assets():
	media = ROOT / "server" / "data" / "media"
	assert media.is_dir()
	assert any(media.iterdir())


def test_seed_catalogue_uses_multiple_existing_images_without_product_json():
	"""The seed script is the catalogue source of truth and every item has a gallery."""
	import ast

	seed = (ROOT / "server" / "scripts" / "seed.py").read_text(encoding="utf-8")
	match = re.search(r"PRODUCT_SOURCE = (\[.*?\])\n\n", seed, re.DOTALL)
	assert match, "PRODUCT_SOURCE should remain a literal, reviewable catalogue"
	products = ast.literal_eval(match.group(1))
	assert len(products) >= 1
	assert all(len(item.get("images", [])) >= 2 for item in products)
	media = ROOT / "server" / "data" / "media"
	assert all(
		(media / image).is_file() for item in products for image in item["images"]
	)
	assert not (ROOT / "server" / "data" / "products.json").exists()


def test_retired_features_have_no_runtime_modules_or_template_controls():
	"""Prevent accidentally reintroducing the removed wishlist/coupon surfaces."""
	app = ROOT / "server" / "app"
	assert not (app / "features" / "wishlist").exists()
	assert not (app / "features" / "coupons").exists()
	for path in (app / "templates").rglob("*.html"):
		text = path.read_text(encoding="utf-8").lower()
		assert "data-wishlist" not in text, path
		assert "coupon code" not in text, path


def test_product_galleries_render_only_one_image_element():
	"""Gallery photos are swapped into one image node instead of relying on CSS hiding."""
	card = (TEMPLATES / "components" / "product" / "card.html").read_text(
		encoding="utf-8"
	)
	product = (TEMPLATES / "pages" / "store" / "product.html").read_text(
		encoding="utf-8"
	)
	assert "data-card-image" in card
	assert "data-image-paths=" in card
	assert "for image in product.images" not in card
	assert "data-gallery-image" in product
	assert "data-image-paths=" in product
	assert "for image in product.images" not in product


def test_page_styles_are_scoped_and_sticky_header_rules_are_not_overridden():
	"""Pages load their own small stylesheet, with no later catch-all overrides."""
	app = ROOT / "server" / "app"
	base = (TEMPLATES / "layouts" / "base.html").read_text(encoding="utf-8")
	header_css = (app / "static" / "css" / "header.css").read_text(encoding="utf-8")
	global_css = (app / "static" / "css" / "base.css").read_text(encoding="utf-8")
	assert 'href="/static/css/pages.css' not in base
	assert 'href="/static/css/catalog.css' not in base
	assert "block page_styles" in base
	assert not (app / "static" / "css" / "pages.css").exists()
	assert "position: sticky" in header_css
	assert "overflow-x: clip" in global_css
	assert "--header-height: 132px" in header_css
	assert "clamp(1.8rem, 4vw, 3rem)" in header_css
	assert ".category-link::before" in header_css
	assert ".category-branch[open] > summary::before" in header_css
	for path in TEMPLATES.rglob("*.html"):
		text = path.read_text(encoding="utf-8")
		if '{% extends "layouts/base.html" %}' in text:
			assert "block page_styles" in text, path


def test_font_awesome_is_self_hosted_and_header_menu_has_a_real_icon():
	"""Header glyphs must not disappear when external CDNs are unavailable."""
	app = ROOT / "server" / "app"
	base = (TEMPLATES / "layouts" / "base.html").read_text(encoding="utf-8")
	icons = (app / "static" / "css" / "icons.css").read_text(encoding="utf-8")
	assert "cdnjs.cloudflare.com" not in base
	assert 'class="fa fa-ellipsis-v"' in base
	assert 'src="/static/js/gallery.js?v=20261015-2" defer' in base
	assert (app / "static" / "js" / "gallery.js").is_file()
	assert "function bindSwipeCarousel" not in (app / "static" / "js" / "site.js").read_text(encoding="utf-8")
	assert "function bindSwipeCarousel" in (app / "static" / "js" / "gallery.js").read_text(encoding="utf-8")
	for module in ("cart.js", "account.js", "product.js"):
		assert (app / "static" / "js" / module).is_file()
		assert f'src="/static/js/{module}?v=20261015-2" defer' in base
	assert "[data-add-cart]" not in (app / "static" / "js" / "site.js").read_text(encoding="utf-8")
	assert "data-checkout-form" not in (app / "static" / "js" / "site.js").read_text(encoding="utf-8")
	assert "fontawesome.woff2" in icons
	assert (app / "static" / "fonts" / "fontawesome.woff2").is_file()


def test_template_fields_and_manufacturing_snapshots_are_migrated_and_used():
	"""New product workflows must work on fresh and previously-created databases."""
	app = ROOT / "server" / "app"
	models = (app / "db" / "models.py").read_text(encoding="utf-8")
	migration = (app / "db" / "session.py").read_text(encoding="utf-8")
	orders = (app / "features" / "orders" / "service.py").read_text(encoding="utf-8")
	admin = (app / "features" / "admin" / "api.py").read_text(encoding="utf-8")
	assert 'fields_schema: Mapped[list]' in models
	assert 'product_details_snapshot: Mapped[dict]' in models
	assert '"product_details_snapshot", "JSON NOT NULL DEFAULT' in migration
	assert '"special_care_snapshot", "BOOLEAN NOT NULL DEFAULT 0"' in migration
	assert 'sku_snapshot=variant_sku or product.sku' in orders
	assert '"variant_meta": variant_meta' in orders
	assert 'meta.get("template_values")' in admin
	assert 'order.status in {"pending", "processing"}' in admin
	assert 'body.status == "paid" and row.status == "cancelled"' in admin


def test_reorder_route_precedes_dynamic_product_route():
	"""The word `reorder` must not be parsed as a numeric product ID route."""
	admin = (ROOT / "server" / "app" / "features" / "admin" / "api.py").read_text(encoding="utf-8")
	assert admin.index('@router.put("/products/reorder")') < admin.index('@router.put("/products/{product_value}")')
	assert 'set(body.ids) != existing' in admin


def test_native_product_image_and_variant_lists_use_drag_drop():
	"""All repeatable product editor rows use one interaction instead of move buttons."""
	editor = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "ProductFormEditors.java").read_text(encoding="utf-8")
	assert editor.count('attachDropTargets(card, row') == 2
	assert 'startDragAndDrop' in editor
	assert 'host.iconButton(R.drawable.ic_add' in editor
	assert 'host.iconButton(R.drawable.ic_delete' in editor
	template_editor = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "TemplateFieldsEditor.java").read_text(encoding="utf-8")
	assert 'valuesForSave()' in template_editor
	assert 'Render Markdown in this value' in template_editor
	assert 'Choose from options' in template_editor
	assert 'Available choices · one per line' in template_editor
	assert 'Default option' in template_editor
	assert 'No default' in template_editor
	assert 'selectedDefault(row.defaultChoice)' in template_editor
	assert '.put("default", defaultValue)' in template_editor
	assert 'Move up' not in editor
	assert 'Move down' not in editor


def test_template_editor_does_not_attach_the_serialized_view_twice_and_exposes_delete_actions():
	"""Opening the template form must not attach a child view to two parents."""
	admin_root = ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin"
	templates = (admin_root / "features" / "AdminTemplatesLayer.java").read_text(encoding="utf-8")
	fields = (admin_root / "TemplateFieldsEditor.java").read_text(encoding="utf-8")
	assert 'content.addView(fieldsEditor.serialized)' not in templates
	assert 'EditText serialized' not in fields
	assert 'private void sync()' not in fields
	assert 'iconButton(R.drawable.ic_delete, "Delete template"' in templates
	assert 'assigned_products' in templates


def test_storefront_templates_do_not_repeat_html_attributes():
	"""Duplicate attributes are browser-dependent and easy to miss in rendered menus."""
	for path in TEMPLATES.rglob("*.html"):
		text = path.read_text(encoding="utf-8")
		assert not re.search(r'<[^>]+\bclass="[^"]*"[^>]+\bclass="', text), path
		assert not re.search(r'<[^>]+\bid="[^"]*"[^>]+\bid="', text), path


def test_admin_common_actions_use_accessible_icons_and_json_helpers_are_extracted():
	"""Repeat list actions stay compact while reusable data parsing lives outside the Activity."""
	admin_root = ROOT / "AdminApp" / "app" / "src" / "main"
	activity = (admin_root / "java" / "nyx" / "velangadmin" / "MainActivity.java").read_text(encoding="utf-8")
	products = (admin_root / "java" / "nyx" / "velangadmin" / "features" / "AdminProductsLayer.java").read_text(encoding="utf-8")
	utilities = (admin_root / "java" / "nyx" / "velangadmin" / "AdminJson.java").read_text(encoding="utf-8")
	for icon in ("ic_add", "ic_edit", "ic_open", "ic_copy", "ic_upload", "ic_delete"):
		assert (admin_root / "res" / "drawable" / f"{icon}.xml").is_file()
	assert 'iconButton(R.drawable.ic_edit, "Edit product"' in products
	assert 'iconButton(R.drawable.ic_open, "Open product on storefront"' in products
	assert 'import static nyx.velangadmin.AdminJson.*;' in products
	assert "static JSONArray parseImages(" in utilities
	assert "static String readableDetails(" in utilities


def test_admin_product_previews_use_the_storefront_renderer():
	"""Preview HTML must come from the same templates and assets as public pages."""
	admin = (ROOT / "server" / "app" / "features" / "admin" / "api.py").read_text(encoding="utf-8")
	preview = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "features" / "AdminPreviewLayer.java").read_text(encoding="utf-8")
	base = (TEMPLATES / "layouts" / "base.html").read_text(encoding="utf-8")
	assert '@router.post("/product-preview")' in admin
	assert '"pages/store/product.html"' in admin
	assert '"pages/store/shop.html"' in admin
	assert 'preview_page="product"' in admin and 'preview_page="card"' in admin
	assert 'class="theme-light{% if request.url.path.startswith' in base
	assert "preview_page|default('') == 'product'" in base
	assert 'preview_mode|default(false)' in base and ' preview-mode{% endif %}' in base
	assert '/api/admin/product-preview' in preview
	assert 'setJavaScriptEnabled(true)' in preview


def test_product_template_values_support_choices_defaults_and_empty_lines():
	"""Optional template fields can stay blank without leaving empty Markdown rows."""
	markdown = (ROOT / "server" / "app" / "core" / "markdown.py").read_text(encoding="utf-8")
	admin = (ROOT / "server" / "app" / "features" / "admin" / "api.py").read_text(encoding="utf-8")
	fields = (ROOT / "server" / "app" / "core" / "template_fields.py").read_text(encoding="utf-8")
	assert '_omit_empty_field_lines(source or "", template_context)' in markdown
	assert 'kind not in {"text", "textarea", "select"}' in admin
	assert '"choices": choices' in admin
	assert 'values.get(key, field.get("default", ""))' in fields
	assert 'prepare_template_field_values(' in (ROOT / "server" / "app" / "web.py").read_text(encoding="utf-8")



def test_preview_interactions_stay_within_the_draft_product():
	"""A draft preview must not navigate into live checkout or external pages."""
	preview = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "features" / "AdminPreviewLayer.java").read_text(encoding="utf-8")
	assert 'loadPreviewPage(view, "product")' in preview
	assert 'loadPreviewPage(view, "card")' in preview
	assert 'External navigation is disabled in preview.' in preview
	assert 'Navigation outside this product preview is disabled.' in preview


def test_template_fields_allow_blank_optional_choices_and_normalize_size_labels():
	"""Optional choice values can be omitted, and settings present readable labels."""
	products = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "features" / "AdminProductsLayer.java").read_text(encoding="utf-8")
	assert 'optionLabels.add("Not specified")' in products
	assert 'spec.optBoolean("required") && !available.isEmpty()' in products
	assert 'sizeModeLabel(productMeta.optString("size_mode", "none"))' in products
	assert 'normalizeSizeMode(sizeMode.getText().toString())' in products
	shell = (ROOT / "AdminApp" / "app" / "src" / "main" / "java" / "nyx" / "velangadmin" / "features" / "AdminShellLayer.java").read_text(encoding="utf-8")
	assert 'Hold a product card and drop it onto another to reorder.' not in shell
