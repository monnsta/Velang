# Administration

The Android administration client is the primary control surface for the store.

## Product authoring

A product can contain:

- identity and SKU
- price and inventory
- images
- categories
- optional variants
- optional Markdown description (hidden when a template is selected)
- optional reusable description template with a structured field builder for labels, stable keys, placeholders, multiline input, required values, and Markdown behavior
- a special-care production flag and private maker notes
- SEO fields
- sizing rules
- arbitrary advanced metadata

The advanced metadata field is an escape hatch. Common controls should be preferred for normal editing.

## Sizing

Set the product's size mode to `none`, `predefined`, `custom`, or `both`.

For predefined sizes, supply the list of accepted values. For custom sizing, supply the measurement field names. Custom measurements are stored with the cart/order item so they remain part of the purchase rather than becoming product-level data.

## Manufacturing queue and order history

The Orders screen has two views of the same data: a production queue grouped by product SKU, variant, customer options, and snapshotted product details; then searchable individual order cards with shipping information, customer notes, status/payment controls, and explicit deletion. The queue includes paid orders that are not delivered or cancelled, and sorts special-care work first. A purchased item's product and variant SKU, template values, variant metadata, production notes, and care/material details are copied to the order item at checkout so catalogue edits do not silently change historical manufacturing instructions.

Deleting a product that has order history is blocked; archive it by changing its status instead. A template assigned to a product cannot be deleted until those products are reassigned. Accounts with order history cannot be deleted, but can be deactivated. The currently authenticated admin account also cannot delete itself.

## Storefront controls

The admin client exposes common site settings for:

- brand/site information
- announcement bar
- footer and static pages
- SEO defaults
- social links
- checkout settings
- the light palette

Theme editing exposes only the light palette; system appearance and dark mode are not supported.

## Development access

The development login exists only outside production. It is useful for local testing and does not require Google credentials. Production disables this route.


## Category hierarchy

Categories are stored with a nullable `parent_id`. Leave it empty for a top-level category; otherwise choose a named category from the Android parent picker. The picker displays full parent paths and excludes choices that would create a cycle. The API independently rejects self-parenting and cyclic trees. Category IDs are stable when category names or slugs change; the editor no longer requires staff to look up and copy numeric IDs manually.

## Development authentication

Development authentication is disabled by default (`DEV_AUTH=false`). Enable it only on a local, non-public development instance. Do not expose the development login endpoint to the internet. For the Android admin app, set a long random `ADMIN_PAIRING_KEY`, pair trusted installations, then rotate or clear the key. Pairing issues a long-lived, revocable device session; the app does not require a Google account. The web-based account/admin sign-in flow remains separate.

## Server URL and HTTPS

The Android app's Server settings verifies the public admin configuration endpoint before persisting a replacement URL. Use an `https://` URL for any public deployment. Terminate TLS at a reverse proxy or managed hosting provider, set `COOKIE_SECURE=true`, and use a strong random `SESSION_SECRET`.


## Pairing the Android app

Set `ADMIN_PAIRING_KEY` to a long random secret on the server before pairing the app. Enter the key once in the app's pairing screen; the app stores the resulting long-lived session token, not the bootstrap key. The key is never served from `/api/admin/config`. Rotate or clear it after pairing trusted devices. Treat the app's local data as a credential: use Android's device lock, and use the app's Logout action to revoke the current session.
