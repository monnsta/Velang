# Architecture notes

The rebuild is feature-oriented rather than layer-oriented.

A feature should be understandable by opening one directory. A normal change usually touches its service, API and/or SSR page without requiring a registry, adapter hierarchy or dependency inversion ceremony.

Use an explicit provider boundary only when the outside implementation is genuinely replaceable. Payment and media are the current examples.

Avoid introducing generic `Repository`, `Manager`, `Factory`, `Resolver`, `ProviderRegistry` and `IWhatever` classes unless there is a concrete second implementation that makes the boundary useful.

## Request paths

Public SSR:

`browser -> FastAPI route -> feature service -> SQLAlchemy -> Jinja template`

Public JSON:

`browser/app JS -> feature API -> feature service -> SQLAlchemy`

Admin:

`native Android app -> /api/admin/* -> admin auth dependency -> feature/service code -> SQLAlchemy`

The admin API does not render a webpage, and the Android app does not render the storefront inside a WebView. Site composition is stored as small JSON settings so content/design can grow without creating a new Python abstraction for every cosmetic change.
