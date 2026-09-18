# Admin model

Admin access is identity-based and server-authorized.

Google ID tokens are verified server-side. Only emails in `ADMIN_EMAILS` can receive an admin session token. Tokens are stored only as SHA-256 hashes in the database, and sessions can be revoked.

The Android client keeps only the opaque token and the configured server URL in private app preferences. There is no client-side admin password.

The admin surface has no SSR/admin webpage. The storefront never exposes an admin link, and the JSON admin routes require a bearer session. Production deployments should still put the server behind HTTPS and, where appropriate, an additional private network/VPN boundary.

The native app intentionally exposes structured controls for routine edits and JSON editors for advanced site composition. The latter is not a database console; all writes still pass through the server API and SQLAlchemy models.

## Controls

The current app can manage products, variants/inventory, categories, reusable product-description templates, content pages, homepage composition, site identity, theme colors, navigation/footer, SEO defaults, social links, checkout settings, coupons, orders, users, media and audit history.
