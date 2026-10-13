from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request
from starlette.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Jinja2Templates(directory=str(ROOT / "server" / "app" / "templates"))


def preview_context(path="/api/admin/product-preview", preview_page="product"):
	request = Request({
		"type": "http",
		"http_version": "1.1",
		"method": "GET",
		"scheme": "https",
		"server": ("store.example", 443),
		"client": ("127.0.0.1", 12345),
		"path": path,
		"raw_path": path.encode("utf-8"),
		"query_string": b"",
		"headers": [],
	})
	return {
		"request": request,
		"site": {
			"site": {"name": "Example Store", "description": "Test storefront", "favicon_path": "/favicon.ico"},
			"theme": {
				"light": {
					"background": "#ffffff", "surface": "#f8f8f8", "text": "#111111",
					"muted": "#666666", "border": "#dddddd", "accent": "#111111",
					"accent_text": "#ffffff",
				},
				"max_width": 1200,
				"radius": 0,
			},
		},
		"title": "Product preview",
		"user": None,
		"cart_count": 0,
		"query": "",
		"nav_categories": [],
		"nav_category_children": {},
		"footer_links": [],
		"now_year": 2026,
		"preview_mode": True,
		"preview_page": preview_page,
	}


def sample_product():
	return SimpleNamespace(
		id=0,
		name="Preview product",
		slug="preview-product",
		sku="PREVIEW-001",
		subtitle="A product under review",
		price=1299.0,
		currency="INR",
		stock_count=4,
		track_inventory=True,
		images=[SimpleNamespace(path="/media/sample.jpg", alt_text="Sample image")],
		variants=[SimpleNamespace(id=1, name="Large", price=1399.0, stock_count=2)],
		meta={"size_mode": "predefined", "predefined_sizes": ["S", "M", "L"], "custom_size_fields": ["width", "length"]},
	)


def test_product_preview_uses_the_actual_storefront_product_template():
	context = preview_context(preview_page="product")
	context.update(product=sample_product(), rendered_description="<p><strong>Fabric:</strong> Cotton</p>")
	response = TEMPLATES.TemplateResponse(context["request"], "pages/store/product.html", context)
	html = response.body.decode("utf-8")

	assert 'class="theme-light product-page preview-mode"' in html
	assert 'href="/static/css/product.css' in html
	assert 'data-add-cart="0"' in html
	assert 'data-variant-select' in html
	assert 'data-size-option="M"' in html
	assert "Fabric:" in html and "Cotton" in html


def test_product_card_preview_uses_the_actual_storefront_card_and_catalog_layout():
	context = preview_context(preview_page="card")
	context.update(products=[sample_product()])
	response = TEMPLATES.TemplateResponse(context["request"], "pages/store/shop.html", context)
	html = response.body.decode("utf-8")

	assert 'class="theme-light preview-mode"' in html
	assert 'href="/static/css/catalog.css' in html
	assert 'class="product-card"' in html
	assert 'data-card-image' in html
	assert 'href="/product/preview-product"' in html
