# Velang

## Stack

- Python 3.11+
- FastAPI / Uvicorn
- SQLAlchemy 2 async + SQLite
- Jinja2 SSR
- Markdown + sandboxed Jinja description templates
- Native Android admin client
- Google Sign-In for production accounts
- Google Pay / UPI integration boundary for checkout

## Run locally

```text
python -m venv .venv
source .venv/bin/activate
python -m pip install -r server/requirements.txt
cp .env.example .env
python server/scripts/seed.py
./server/run.sh
```

Open `http://127.0.0.1:8000`.

Development authentication is disabled by default. To test the customer sign-in flow locally without Google credentials, explicitly set `DEV_AUTH=true` in `.env`; do not expose that server publicly. The Android admin app uses a separate device-pairing key, not the development login.

## Production authentication

For a public deployment, set `APP_ENV=production`, a strong random `SESSION_SECRET`, `COOKIE_SECURE=true`, and `DEV_AUTH=false`. Configure `GOOGLE_WEB_CLIENT_ID` for customer sign-in. For the Android admin app, configure a separate long random `ADMIN_PAIRING_KEY`, pair trusted devices, then rotate the pairing key. Google web-admin access remains restricted by `ADMIN_EMAILS` and the user's admin flag.

## Payments

The checkout layer is provider-oriented without making the rest of the application provider-dependent. Development uses the local/manual payment implementation.

For India production checkout, configure the Google Pay / UPI integration described in `docs/ARCHITECTURE.md` and your payment provider's server-side verification requirements. Do not treat a client-created UPI URI as proof of payment.

## Native admin app

The Android project is under `AdminApp/`.

For a local server on the Android emulator, use the emulator's host address. For a physical phone, use the machine's reachable LAN address or HTTPS deployment.

On first launch, enter the server URL and pairing key once. The app verifies the server, stores its URL and a revocable device token, and does not ask for the URL again unless you change it or the connection stops working. No Google account is required in the Android admin app.

The app controls:

- products, variants, inventory and categories, with drag-and-drop reordering
- optional description templates with validated dynamic fields
- media upload and asset selection
- searchable order cards and a grouped production queue with special-care flags
- safe deletion of orders and unused accounts (historic accounts are deactivated instead)
- users
- content pages
- storefront theme and reusable light-palette controls
- navigation, footer, SEO, social and checkout settings
- audit history

## Product descriptions

A product does not require a description template.

Normal products can use Markdown directly. A description template is an optional reusable Markdown/Jinja document selected for products that share a structure. Variables come from the product object, including custom metadata:

```text
# {{ product.name }}

{{ product.description }}

Material: {{ product.meta.material }}
```

This means the template owns the repeated structure while each product only supplies its changing values.

Templates can also define structured fields through a field builder in the admin app: each field has a stable key, label, optional placeholder, single-line or multiline input, a required flag, and a Markdown toggle. The template reads these values through `product.fields`, for example `{{ product.fields.story }}`. Ordinary fields are escaped so punctuation cannot accidentally become headings, links, or emphasis; enable Markdown only for fields where formatted content is intentional. See [`docs/DESCRIPTION_TEMPLATES.md`](docs/DESCRIPTION_TEMPLATES.md) for the schema format.

Products may be flagged for special care and carry private production notes for the maker. When an order is placed, its SKU (including the chosen variant SKU), template values, variant metadata, and production instructions are snapshotted onto the order item. Later product edits therefore do not rewrite the instructions attached to existing orders. The admin Orders screen puts paid, unfinished work into a grouped production queue, prioritizes special-care items, and shows customer options, quantities, related order numbers, and maker notes. Product templates and products referenced by historic orders cannot be deleted without first resolving those references; deleting an order or an unused account remains possible with an explicit confirmation.

## Sizes

Products can use one of three modes:

- `predefined` — only configured sizes
- `custom` — exact customer measurements
- `both` — either option

The mode and fields are stored with the product's metadata so products that do not need sizing are not forced to have it.

## Storefront design

The storefront uses a restrained visual system: mostly monochrome, thin borders, large typography, image-led product cards, and no decorative shadows. The homepage directly lists the active catalogue; there is no featured/collections landing-page layer.

The storefront uses a single light palette and ignores operating-system appearance.

### Front-end asset layout

The base layout loads only the shared reset/type rules, header/navigation, common controls, and the self-hosted Font Awesome glyph subset. Templates load a page stylesheet through the `page_styles` block: catalog cards, product detail, account/cart, content, and sign-in layouts remain separate instead of accumulating overrides in one global file. When changing a component, update the rule in its owning stylesheet rather than appending another specificity workaround.

Product cards and product detail galleries each keep exactly one image element in the rendered layout. Their image paths and alt text are held as JSON data attributes; `gallery.js` swaps the active image and moves the thin progress rail after a horizontal swipe, while `site.js` handles shared cart and navigation behavior. Product-card information reserves two title lines, so every price begins at the same vertical position regardless of title length. The sticky header height is defined once in `header.css`, with responsive sizing and transparent/solid product-page states managed there.

## Formatting

Run:

```text
./format.sh
```

It formats Python, Jinja templates, web assets and Android Java when the corresponding tools are installed.

Python indentation is normalized to literal tabs after Ruff formatting to match the project's source style.

Install development tooling with:

```text
python -m pip install -r server/requirements-dev.txt
```

## Tests

Run the complete server suite with:

```text
PYTHONPATH=server pytest -q
```

The suite covers Markdown/Jinja rendering and sanitization, site defaults and theme merging, authentication sessions, catalog operations, product search, custom sizing validation, and public configuration contracts. Integration tests use an isolated in-memory SQLite database.

## Project layout

```text
server/app/
├── core/           shared application concerns
├── db/             SQLAlchemy models and database lifecycle
├── features/       feature-owned behavior and APIs
├── templates/
│   ├── layouts/    global layouts
│   ├── components/ reusable visual pieces
│   └── pages/      route-oriented pages
├── static/
│   ├── css/        shared chrome and page-specific stylesheets
│   └── js/         focused site, cart, account, product, and gallery modules
└── web.py          SSR route composition

AdminApp/            native Android administration client
  └── .../nyx/velangadmin/
      ├── MainActivity.java          navigation and screen composition
      ├── AdminJson.java             reusable data parsing/display helpers
      ├── ProductFormEditors.java    product image and variant editing
      └── TemplateFieldsEditor.java  structured template-field builder
docs/                architecture and content authoring notes
scripts/             development tooling
```


## HTTPS and a custom domain

For a public deployment, point your domain's DNS records at the server or reverse proxy, then terminate TLS at Caddy, nginx, or your hosting platform. Keep Uvicorn bound to a private interface behind that proxy; do not expose the application process directly to the internet. Configure the proxy to forward the original host and HTTPS scheme so redirects and absolute URLs use the public domain. Caddy can obtain and renew certificates automatically once DNS points to the host and ports 80/443 are reachable.

The Android admin app accepts a full `https://` server URL. On first launch, pair the device with `ADMIN_PAIRING_KEY`; the URL is only a connection setting, not an authentication secret. Use the app's **Server** control to verify and save a changed address. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for a working Caddy example and setup checklist.


### Security defaults

Development sign-in is disabled by default. Keep `DEV_AUTH=false` outside isolated local development. For public deployments, use HTTPS, set `COOKIE_SECURE=true`, configure a strong `SESSION_SECRET`, and use the admin app pairing flow with a private `ADMIN_PAIRING_KEY`. The admin app stores a long-lived, revocable device token after pairing; it does not need a Google account.

### Nested categories

Categories support arbitrary depth through `parent_id`. The API rejects parent cycles. Existing SQLite databases are upgraded on startup to add the nullable parent column.

### Removed features

Wishlist and coupon endpoints are not mounted, their active implementation modules have been removed, and checkout no longer accepts coupon codes. Existing order totals are preserved when the retired coupon tables and coupon-only order columns are removed during SQLite startup migration. New orders use catalogue prices.

## Deployment with automatic HTTPS

A Docker Compose + Caddy deployment is included for a simple custom-domain setup. Copy `.env.example` to `.env`, set your domain and strong session/pairing secrets, point the domain DNS at your server, allow ports 80/443, then run `docker compose up -d --build`. Caddy automatically provisions and renews TLS certificates. Full steps and caveats are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Building the Android admin app

`AdminApp/` is a standalone Android Gradle project. Open that directory in Android Studio with Android SDK 35 installed, let Gradle sync, then run the `app` configuration. The app uses Java 11 language settings and supports Android 8.0 (API 26) and newer. Its optional dark theme is app-local and does not change storefront theme settings.
