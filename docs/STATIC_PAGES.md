# Static pages

Storefront information pages live in `server/content/pages/` as Markdown files.

Each file is named `<slug>.md` and can contain a small front matter header:

```md
---
title: Shipping
---

Your Markdown content goes here.
```

The filename becomes the URL at `/pages/<slug>`. Every Markdown page is automatically listed in the storefront footer, so adding a new file also adds its footer link.

Static Markdown files take precedence over legacy `content_pages` database rows. The database content remains available as a compatibility fallback for existing installations and the admin API.


## Store variables and collapsible sections

Markdown is rendered with the sandboxed Jinja environment used by product descriptions. The `site` object exposes the current store configuration, for example `{{ site.site.name }}` and `{{ site.site.description }}`. Product description templates also retain their `product` object.

Use a collapsible block anywhere in a static page, custom page, or product description:

```markdown
::: collapse Delivery and returns

Orders are prepared carefully. See [the return policy](/pages/return-policy) for details.

:::
```

Add `open` after `collapse` to start the section expanded: `::: collapse open Delivery and returns`. Collapsible bodies support normal Markdown, including links, lists, and images.
