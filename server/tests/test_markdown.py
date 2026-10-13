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


def test_markdown_supports_store_variables():
	from app.core.markdown import render

	assert render("Welcome to **{{ site.site.name }}**.", {"site": {"site": {"name": "Velang Lab"}}}) == "<p>Welcome to <strong>Velang Lab</strong>.</p>\n"


def test_markdown_supports_reusable_collapsible_sections():
	from app.core.markdown import render

	html = render("::: collapse Delivery details\nShips in 2–4 days.\n:::")
	assert '<details class="accordion">' in html
	assert '<summary><span class="accordion-title">Delivery details</span></summary>' in html
	assert "Ships in 2–4 days." in html


def test_markdown_collapsible_title_is_escaped_and_unsafe_links_remain_blocked():
	from app.core.markdown import render

	html = render('::: collapse <img src=x onerror=alert(1)>\n[bad](javascript:alert(1))\n:::')
	assert "<img" not in html
	assert "onerror" not in html
	assert "javascript:" not in html


def test_plain_template_values_escape_markdown_and_preserve_line_breaks():
	from app.core.markdown import escape_plain_template_value, render

	plain = escape_plain_template_value("First line\n# this stays text\nThird line")
	html = render(plain)
	assert "First line<br>" in html
	assert "Third line" in html
	assert "<h1>this stays text</h1>" not in html
