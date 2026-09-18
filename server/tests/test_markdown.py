from app.core.markdown import render


def test_template_and_markdown_rendering():
	html = render(
		"# {{ product.name }}\n\n**SKU:** {{ product.sku }}",
		{"product": {"name": "Test", "sku": "ABC-1"}},
	)
	assert "<h1>Test</h1>" in html
	assert "<strong>SKU:</strong> ABC-1" in html


def test_html_is_sanitized():
	html = render("<script>alert('x')</script>\n\nHello")
	assert "<script" not in html.lower()
	assert "Hello" in html
