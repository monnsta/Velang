from app.core.markdown import render


def test_template_can_use_arbitrary_product_variables():
	html = render(
		"## {{ product.name }}\n\nMaterial: {{ product.meta.material }}\n\n{{ product.description }}",
		{
			"product": {
				"name": "Example",
				"description": "Plain markdown remains valid.",
				"meta": {"material": "Cotton"},
			}
		},
	)
	assert "<h2>Example</h2>" in html
	assert "Material: Cotton" in html
	assert "Plain markdown remains valid." in html


def test_template_html_cannot_escape_markdown_sanitizer():
	html = render("[bad](javascript:alert(1))\n\n<img src=x onerror=alert(1)>")
	assert "javascript:" not in html
	assert "onerror" not in html


def test_optional_template_fields_remove_their_line_and_excess_spacing():
	html = render(
		"## Details\n\n**Fit:** {{ product.fields.fit }}\n\n**Fabric:** {{ product.fields.fabric }}\n\n**Care:** {{ product.fields.care }}",
		{"product": {"fields": {"fit": "", "fabric": "Cotton", "care": "Cold wash"}}},
	)
	assert "Fit:" not in html
	assert "Fabric:" in html and "Cotton" in html
	assert "Care:" in html and "Cold wash" in html
	assert "\n\n\n" not in html


def test_optional_template_field_can_remove_a_whole_separated_section():
	html = render(
		"**Material:** {{ product.fields.material }}\n\n**Care:** {{ product.fields.care }}",
		{"product": {"fields": {"material": "", "care": "Cold wash"}}},
	)
	assert "Material:" not in html
	assert html.count("<p>") == 1
	assert "Care:" in html



def test_template_fields_apply_defaults_and_preserve_optional_blank_choices():
	from app.core.template_fields import prepare_template_field_values

	schema = [
		{"key": "fabric", "type": "select", "choices": ["100% cotton", "Cotton / linen"], "default": "Cotton / linen"},
		{"key": "fit", "type": "select", "choices": ["Regular", "Relaxed"], "default": "", "required": False},
		{"key": "care", "type": "select", "choices": ["Cold wash", "Dry clean"], "required": True},
		{"key": "notes", "type": "text", "default": "Use *gentle* care."},
	]
	prepared = prepare_template_field_values(schema, {"fit": ""})

	assert prepared["fabric"] == "Cotton / linen"
	assert prepared["fit"] == ""
	assert prepared["care"] == "Cold wash"
	assert prepared["notes"] == r"Use \*gentle\* care\."
