# Architecture

## Boundaries

The application has four useful boundaries:

1. **Features** own business behavior.
2. **Core** owns cross-feature infrastructure such as configuration, security, Markdown rendering and site settings.
3. **Database** owns persistence models and session lifecycle.
4. **External integrations** are introduced only where replacing the provider is a realistic requirement.

There is deliberately no generic service/repository/factory layer around ordinary features.

## SSR

Jinja templates are rendered by FastAPI. The browser receives complete pages and uses a small JavaScript layer for interactions such as cart updates, Google login callbacks and mobile navigation.

Templates are organized as:

- `layouts/` — global document structure
- `components/` — reusable visual fragments
- `pages/` — pages grouped by purpose

Route code refers to those paths explicitly. A template does not need a framework-specific component registry.

## Product descriptions

`Product.description` is always usable Markdown.

`DescriptionTemplate` is optional. When selected, its body is rendered as sandboxed Jinja first and Markdown second. The template receives a product dictionary containing normal fields and the product's `meta` object.

The product therefore owns values while the template owns repeated presentation structure.

## Homepage

Homepage content lives in the `homepage` site setting as a list of small blocks. Supported blocks include:

- hero
- editorial
- featured/latest products
- category strips
- quote
- rich text

The Android admin app can add and edit the common block fields. The raw setting remains available through the server API for advanced composition.

## Theme

Theme settings contain one light palette, radius and maximum content width. Legacy dark/system keys are discarded when storefront settings are loaded.

## Authentication

Production storefront authentication is Google-only. Google ID tokens are verified server-side before the session is created.

Development authentication is intentionally separate and is disabled automatically by `APP_ENV=production` or explicitly with `DEV_AUTH=false`.

Admin sessions are opaque random tokens. Only a SHA-256 hash is stored in the database. Production admin accounts are additionally restricted by the configured administrator email allow-list.

## Media

Uploaded product/media files are stored under `server/data/media` in development. The `/media` route exposes only that directory. A production deployment can replace the storage implementation with object storage without changing catalog or storefront behavior.

## Payments

Checkout calls a payment integration boundary. The order service does not know provider-specific request formats. Production payment confirmation must come from a trusted server-side verification/webhook flow; a client-side success page is never treated as payment proof.


## Storefront presentation conventions

- The landing route is the full active product catalogue; category navigation is the only catalogue drawer.
- Product-card markup is a dedicated partial so purchasing contexts can introduce another card without coupling it to catalogue cards.
- Product images are ordered by `ProductImage.position`; the seed reconciles the entire gallery from `PRODUCT_SOURCE`.
- Prices remain numeric in the database and are formatted at render time from their ISO 4217 currency code.
- The storefront intentionally uses the light palette regardless of operating-system appearance. Shared interaction styles live in `base.css`, with component-specific layout styles kept in their own files.
