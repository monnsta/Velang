# Velang Rebuild

A clean rebuild of the Velang storefront and admin system.

The old projects are kept as **design and feature references**, not as architectural dependencies. The rebuild uses one FastAPI application that owns the storefront, server-rendered HTML, JSON APIs and SQLite database, plus a **native Android admin app**.

## What changed

- FastAPI + async SQLAlchemy + SQLite.
- Server-side rendered storefront with Jinja templates; there is no separate frontend application.
- Feature-oriented backend packages instead of a generic extension / wrapper / repository stack.
- Integration boundaries only where changing the implementation actually matters (payment/media).
- Reusable Markdown + sandboxed Jinja description templates for product types.
- Product variants, inventory, categories, SEO fields, metadata, images, coupons, wishlists, addresses, orders, users and audit logs.
- Editable site theme, navigation, footer, homepage sections, SEO defaults, social links and checkout settings from the admin app.
- Native Android admin app. It is **not a WebView**.
- Google Sign-In through Google Identity / Android Credential Manager for admin access.
- Delhivery and PhonePe are intentionally not included.

## 1. Run the server locally

From the repository root:

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cp .env.example .env
```

Change at least:

```text
SESSION_SECRET=...a long random value...
ADMIN_EMAILS=your-google-account@example.com
```

Then seed demo data:

```text
PYTHONPATH=server python server/scripts/seed.py
```

Start the server:

```text
./server/run.sh
```

Open `http://127.0.0.1:8000/`.

Run the included lightweight tests with:

```text
pytest -q server/tests
```

FastAPI API docs are available at `/api/docs` while `APP_ENV=development`.

## 2. Google setup

The project has two Google sign-in surfaces: the storefront and the native admin app.

Create or use one Google Cloud project and open **Google Auth Platform**. Configure the app's branding / consent information and create a **Web application client ID**. Put that client ID in:

```text
GOOGLE_WEB_CLIENT_ID=...
```

The server verifies the Google ID token against that client ID. The Android admin app asks the server for the same public client ID at `/api/admin/config`, then uses Android Credential Manager to obtain the Google ID token.

Google's current Android guidance uses Credential Manager for Sign in with Google and says the ID token returned by the app should be validated by the server. The current stable Credential Manager release is 1.6.0, and the current Google ID SDK release is 1.2.1.

## 3. Locking down the admin

The admin is intentionally **not a webpage** and the storefront has no admin link.

Access requires all of the following:

1. A valid Google ID token.
2. The Google email must be present in `ADMIN_EMAILS`.
3. The server issues an opaque, database-backed admin session token.
4. Every native admin request sends that token as `Authorization: Bearer ...`.

For a real deployment, put the FastAPI server behind HTTPS and set:

```text
COOKIE_SECURE=true
APP_ENV=production
```

For stronger isolation, keep the admin API behind a VPN, private reverse proxy or another network access control layer. The allowlist is the identity gate; it is not a substitute for network security.

## 4. Native admin app

Open `AdminApp/` in Android Studio, or build from Termux. The project uses AGP 9.4.0, which requires Gradle 9.6.0 or newer; use a compatible Gradle/JDK 17+ setup:

```text
gradle -p AdminApp :app:assembleDebug
```

The package name is:

```text
nyx.velangadmin
```

On first launch, enter the server URL, save it, then use **Sign in with Google**.

The app currently exposes:

- dashboard counts
- product editor
- category editor
- Markdown/Jinja description template editor
- order status + payment status controls
- coupon editor
- content page editor
- site/theme/navigation/homepage/SEO/social/checkout settings
- user activation/admin controls
- media upload and listing
- audit log endpoint for future UI expansion

## 5. Product description templates

Descriptions are not hardcoded into each product anymore.

A template can look like:

```text
# {{ product.name }}

{{ product.subtitle }}

{{ product.description }}

**Material:** {{ product.material }}

**SKU:** {{ product.sku }}
```

A product stores dynamic values and points to the template. Different product types can use different templates, and a product can explicitly choose which template to use.

Templates are rendered through Jinja's sandbox and then passed through Markdown + HTML sanitization. Raw HTML is disabled in product Markdown.

## 6. Homepage / theme controls

The storefront is intentionally data-driven without turning the entire backend into a plugin framework.

Homepage blocks support types such as:

- `hero`
- `editorial`
- `featured_products`
- `latest_products`
- `category_strip`
- `quote`
- `text`

The admin app can edit the complete JSON for these structures. That is the advanced escape hatch; everyday product and category fields still have dedicated controls.

Theme settings cover the small visual system rather than forcing dozens of design tokens:

- background
- surface
- text
- muted text
- border
- accent
- accent text
- corner radius
- max content width

The visual defaults intentionally stay close to the old Velang language: monochrome, flat, editorial, sparse and mostly boxy.

## 7. Payments

`PAYMENT_PROVIDER=dev` is the local/test mode.

The Google-oriented provider stores the merchant VPA, amount and transaction reference needed to build a UPI payment request, but **production payment settlement / verification is not falsely presented as complete**. Before launch, the merchant account, PSP flow and server-side transaction verification need to be configured for the chosen Google Pay / UPI integration.

## 8. Storage

Local media is stored in:

```text
server/data/media/
```

Uploads go to:

```text
server/data/media/uploads/
```

The database stores the public media path. A future Google Cloud Storage backend can be added behind the existing media boundary without changing product/page code.

## 9. Database

The first run creates `server/database/velang.db` with SQLAlchemy metadata.

For a production deployment, introduce Alembic migrations before changing schema on an existing live database. The current project deliberately starts with `create_all()` so a fresh clone remains immediately runnable.

## 10. Project layout

```text
server/app/
├── core/                  # configuration, security, site settings, Markdown rendering
├── db/                    # SQLAlchemy models and session setup
├── features/
│   ├── auth/
│   ├── catalog/
│   ├── cart/
│   ├── wishlist/
│   ├── addresses/
│   ├── orders/
│   ├── coupons/
│   ├── content/
│   ├── media/
│   ├── payments/
│   └── admin/
├── templates/             # SSR UI
├── static/                # CSS, JS, fonts and artwork
└── web.py                 # storefront routes

AdminApp/
└── app/src/main/java/nyx/velangadmin/
```

The intended rule is simple: **features own business behavior; integrations own external providers; core owns cross-cutting concerns.** There is no requirement to create an interface for every class.

## 11. Secrets from the old projects

Do not copy credentials, API tokens, cookies or other secrets from the old archives into this repository. Put them in `.env` or the platform's secret manager instead.

If any credential in an old archive was real, rotate it.

## 12. Local Android note

The native admin app defaults to `http://127.0.0.1:8000`, which is convenient when the server is running on the same Android device through Termux. The APK permits cleartext HTTP for this local/dev workflow. For a deployed admin server, use an HTTPS URL and keep the server behind normal network controls.

## 13. Admin controls

The native admin app intentionally exposes both structured editors and advanced JSON editors. The structured controls cover the common path (product/catalog fields, theme colors, inventory, orders, coupons, users, uploads, etc.); JSON is there for homepage blocks, navigation, metadata, SEO, and future settings without forcing a schema migration for every cosmetic/content change.

The audit screen shows the latest changes made through the admin API.
