# Aviva analytics configuration

<!--- TOC -->

* [Sentry](#sentry)

<!--- END -->

## Sentry

Aviva Android supports the approved Aviva-owned Sentry project. PostHog is disabled, and Element Sentry/PostHog/Rageshake credentials are not consumed by Aviva builds.

Set the Sentry DSN in ignored `local.properties` or provide it through `AVIVA_SENTRY_DSN`:

The format used to add the DSN to your `local.properties` file is the following:

```properties
services.sentry.dsn=<Aviva Sentry DSN>
```

The same DSN is used for native and Rust reporting unless `services.sentry.rustDsn` or `AVIVA_SENTRY_RUST_DSN` supplies a separate Aviva DSN. Embedded-call Sentry uses `services.sentry.dsn` / `AVIVA_SENTRY_DSN`; PostHog and Rageshake remain unset.

The DSN is sufficient for runtime event ingestion. Uploading R8 mappings or native symbols for de-obfuscated reports requires a Sentry auth token and project metadata; supply those through protected local/CI configuration only. Never put DSNs or auth tokens in tracked source, plans, or logs.
