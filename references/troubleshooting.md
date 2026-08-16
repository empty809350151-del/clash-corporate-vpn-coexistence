# Troubleshooting

## Fake-IP still appears

- Confirm the active generated config contains `enhanced-mode: redir-host`.
- Confirm the active profile references the patched merge enhancement.
- Reload the core, then flush application DNS caches or restart affected applications.
- Do not change to another synthetic range until checking all company, LAN, VM, and container routes.

## HTTPS certificate mismatch remains

- Treat this as failure; never bypass validation with `curl -k` or browser warning overrides.
- Resolve the hostname and check whether it lands in a synthetic range.
- Inspect the longest-prefix route for that address. A corporate route can outrank Clash's broad TUN routes.
- Confirm the Clash core actually reloaded the patched generated config.

## Company IP works but company hostname fails

- This indicates split-DNS rather than route failure.
- Discover the company DNS server from the company VPN before enabling Clash.
- Add a domain-specific DNS policy only after the user supplies or verifies the company suffix.
- Never send unknown company names to a public DNS resolver.

## Company resources fail only in browsers

- Confirm macOS system proxy flags are disabled while TUN remains enabled.
- Browsers using an extension-level proxy can still bypass the operating-system route table; disable or exclude company domains in that extension.

## Public proxy traffic fails

- Confirm Clash TUN is still active and owns broad public prefixes.
- Test a raw public IP separately from DNS.
- Test an HTTPS site expected to use the proxy.
- If raw IP works but names fail, diagnose DNS. If both fail, diagnose the proxy node or TUN route.

## Route ownership interpretation

- The physical interface normally owns the default gateway.
- Company VPNs often install many specific prefixes; those should beat broad TUN routes by longest-prefix matching.
- Clash TUN often installs broad complementary routes rather than replacing the literal default route.
- Interface numbers such as `utun4` and `utun6` are ephemeral and must not be persisted in configuration.
