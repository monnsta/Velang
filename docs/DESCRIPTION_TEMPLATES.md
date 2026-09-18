# Description templates

Product templates are Markdown documents with sandboxed Jinja substitutions.

Example:

`# {{ product.name }}`

`{{ product.description }}`

`**Material:** {{ product.material }}`

`**Care:** {{ product.care }}`

Available product fields are documented by the admin UI and are intentionally plain data values.

The render pipeline is:

`Jinja sandbox -> CommonMark -> Bleach allowlist`

Raw HTML is disabled before sanitization.
