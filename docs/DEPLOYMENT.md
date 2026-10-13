# Deployment, HTTPS, and custom domains

Velang does not need a hard-coded public domain. Point your domain at the server or reverse proxy, and the same SSR application serves it using the incoming host.

## 1. DNS

Create an `A` record for the domain (and an `AAAA` record only if IPv6 is configured) pointing at the public server address. If using a subdomain such as `shop.example.com`, create the record for that subdomain.

## 2. Run Velang privately

Set the server to listen only on loopback behind the proxy:

```sh
HOST=127.0.0.1 PORT=8000 APP_ENV=production COOKIE_SECURE=true DEV_AUTH=false ./server/scripts/start_prod.sh
```

Configure a strong `SESSION_SECRET`, the Google web client ID for customer sign-in, and a long random `ADMIN_PAIRING_KEY` for the Android admin app. Generate secrets locally with:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Do not reuse the same secret for `SESSION_SECRET` and `ADMIN_PAIRING_KEY`. Keep `.env` private and out of version control.

## 3. Terminate TLS with Caddy

A minimal Caddyfile for a domain with working public DNS:

```text
shop.example.com {
	reverse_proxy 127.0.0.1:8000
}
```

Caddy obtains and renews certificates automatically when DNS and inbound HTTP/HTTPS access are configured correctly. Nginx, a managed hosting proxy, or another TLS terminator can be used instead; proxy requests to the private Uvicorn port and preserve the original host and forwarded scheme.

## 4. Verify

- Open `https://shop.example.com/` and confirm the browser reports a valid certificate.
- Check `https://shop.example.com/health` returns `{"ok":true,...}`.
- Set `COOKIE_SECURE=true` when HTTPS is active so session cookies are marked Secure.
- Open the Android admin app, enter the HTTPS URL and pairing key once, and confirm the dashboard loads.
- After pairing trusted devices, rotate the pairing key to prevent new pairings with the previous secret. Existing device sessions are separately revocable; clearing the pairing key does not revoke sessions already issued.

HTTPS cannot be enabled by an application setting alone: DNS, a reachable host, and a TLS certificate/proxy must also be configured.

## Quick deployment with Docker Compose

For a new single-server deployment, Compose builds the application and runs Caddy in front of it. Caddy handles certificate requests and renewals; the only domain-side step is pointing DNS at the host and allowing inbound TCP ports 80 and 443.

1. Copy `.env.example` to `.env` and replace `DOMAIN`, `SESSION_SECRET`, and `ADMIN_PAIRING_KEY`. Generate strong, different secrets with `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Set `GOOGLE_WEB_CLIENT_ID` and `ADMIN_EMAILS` as needed.
2. Point the domain's DNS `A` record at the server. Configure `AAAA` only if the server actually accepts IPv6 traffic.
3. Run `docker compose up -d --build` from the project root.
4. Confirm `https://your-domain.example/health` returns a healthy response, then pair the Android admin app using the HTTPS URL and pairing key.

The SQLite database stays in `database/` and uploaded media stays in `server/data/media/` on the host. Back up both directories. Keep `.env` out of backups that are shared publicly, and never commit it. Certificate issuance requires a real domain, correct DNS, and reachable ports; Compose cannot configure DNS at the registrar on your behalf.
