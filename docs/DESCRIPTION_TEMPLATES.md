# Description templates

A description template is optional.

Use ordinary Markdown in the product when a product has a unique description. Create a template when several products share a structure.

Templates use Jinja variables and then pass through the same Markdown renderer as ordinary descriptions.

Example:

```text
# {{ product.name }}

{{ product.description }}

**Material:** {{ product.meta.material }}
**Finish:** {{ product.meta.finish }}
```

A product can therefore provide:

```text
meta = {
	"material": "100% cotton",
	"finish": "Garment washed",
}
```

The renderer uses a sandboxed Jinja environment and sanitizes the resulting HTML before it reaches the storefront.


## Structured template fields

Templates can declare fields in `fields_schema`, then use their values in the body as `{{ product.fields.story }}`. The schema is a JSON array; each entry has a stable `key`, a human-facing `label`, `type` (`text` or `textarea`), and optional `markdown`, `required`, and `placeholder` values:

```json
[
	{"key": "story", "label": "Craft story", "type": "textarea", "markdown": true, "required": true},
	{"key": "fabric", "label": "Fabric", "type": "select", "choices": ["100% cotton", "50% cotton / 50% linen"], "default": "100% cotton"},
	{"key": "fit", "label": "Fit", "type": "text", "placeholder": "Optional fit description"}
]
```

Values are stored on the product under `meta.template_values`. Fields marked `markdown: false` are escaped before template rendering so customers cannot accidentally turn ordinary text into headings, links, or emphasis. When a template is selected, the admin editor hides the product's standalone Markdown description and displays only the fields requested by the template.


Optional fields can be left blank. When a Markdown line depends directly on a blank field—for example, `**Fit:** {{ product.fields.fit }}`—the renderer omits that line and collapses repeated blank lines, keeping the finished description compact. A select field can explicitly be set to “Not specified” when it is optional; its configured default is used only when no product-level value has been saved.

The Android admin preview requests rendered HTML from the server's `/api/admin/product-preview` endpoint. Product cards and product pages therefore use the same Jinja templates, stylesheets, and storefront scripts as the public website, with cart and checkout actions disabled in preview mode.
