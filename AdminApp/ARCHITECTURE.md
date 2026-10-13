# Velang Admin App Architecture

Velang Admin remains a single-Activity app. `MainActivity` is the only Activity declared in the
manifest. The feature classes are **abstract behavior layers**, not separately launched Activities;
they inherit a shared `AdminCoreActivity` so all UI work continues to run on the same Activity instance
without duplicating navigation state or creating a second controller lifecycle.

## Source map

- `app/src/main/java/nyx/velangadmin/MainActivity.java` — minimal manifest entry point.
- `.../core/AdminCoreActivity.java` — common Activity state, reusable controls, asynchronous API
  execution, and the method contracts connecting feature modules.
- `.../features/AdminShellLayer.java` — device pairing/login, application chrome, navigation history,
  drawer, server settings, logout, and back-button behavior.
- `.../features/AdminDashboardLayer.java` — dashboard summary.
- `.../features/AdminProductsLayer.java` — product listing, reorder, forms, variant/image editors,
  template values, special-care and production fields, plus validation.
- `.../features/AdminCategoriesLayer.java` — category editing and parent-cycle validation.
- `.../features/AdminTemplatesLayer.java` — description template list and field-schema editor.
- `.../features/AdminOrdersLayer.java` — order list, payment/status changes and production details.
- `.../features/AdminPagesLayer.java` — static/custom page management and Markdown previews.
- `.../features/AdminUsersLayer.java` — user list and access toggles.
- `.../features/AdminSiteLayer.java` — storefront settings and theme editor.
- `.../features/AdminMediaLayer.java` — media library, uploads, alt text and file selection.
- `.../features/AdminPreviewLayer.java` — HTML, product and Markdown previews.
- `.../features/AdminAuditLayer.java` — audit history.
- `AdminApi.java` — HTTP transport. Keep calls inside `async` or `asyncAction` for screen actions.
- `AdminJson.java` — public JSON conversion/validation utility shared by the feature packages.
- `ProductFormEditors.java` and `TemplateFieldsEditor.java` — reusable structured form components.
- `ColorWheelView.java` — theme-color wheel.

## Adding or changing a screen

1. Put the page implementation and its local helpers in its matching `features/` layer.
2. Add a `protected abstract` method contract to `AdminCoreActivity` when one feature needs to call a
   method implemented by another feature layer.
3. Add page routing and navigation labels in `AdminShellLayer` (`loaderForPage` and `showShell`).
4. Keep network requests off the main thread with `async`/`asyncAction`; only touch views on the UI thread.
5. Prefer `field`, `sectionHeading`, `confirm`, `iconButton`, `label`, and `button` for shared UI.

## Build

Open `AdminApp/` in Android Studio or run `gradle :app:assembleDebug` with the Android SDK and a
compatible Gradle installation. The app uses `compileSdk 35`; only `MainActivity` needs a manifest entry.
