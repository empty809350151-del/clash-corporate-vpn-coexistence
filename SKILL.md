---
name: clash-corporate-vpn-coexistence
description: Diagnose and safely configure Clash Verge Rev TUN alongside a corporate VPN on macOS. Use when multiple utun interfaces coexist, company intranet routes must remain reachable, Clash Fake-IP overlaps 198.18.0.0/15, HTTPS certificates mismatch, DNS returns 198.18.x.x, or both system proxy and TUN are enabled. Provides backup, dry-run, apply, verification, and rollback workflows without exposing subscriptions or proxy credentials.
---

# Clash and corporate VPN coexistence

Keep the corporate VPN's specific routes while letting Clash TUN handle remaining public traffic. Prefer `redir-host` and TUN-only operation when a corporate client owns Clash's Fake-IP range.

## Safety rules

- Support macOS and Clash Verge Rev only. Stop if the client or operating system differs.
- Treat VPN, proxy, DNS, and route changes as security-sensitive network changes. Obtain explicit confirmation immediately before applying them.
- Diagnose read-only first. Never remove company routes, disable the company VPN, expose subscription URLs, or print proxy credentials.
- Back up every modified file. Use the supplied patcher, whose default mode is dry-run.
- Do not hardcode `utun` numbers: macOS can renumber them after reconnecting.
- Do not bypass certificate warnings. A certificate mismatch is a failed verification.

## Workflow

### 1. Inspect

Run:

```bash
bash scripts/inspect_macos_network.sh
```

Confirm all of the following before proposing a change:

- One physical default route exists, usually Wi-Fi or Ethernet.
- The company VPN owns specific destination prefixes.
- Clash TUN owns broad public prefixes.
- Clash uses Fake-IP and the company VPN owns an overlapping pool, commonly `198.18.0.0/15`.
- System proxy and TUN are both enabled, creating double interception.

Infer ownership from route shape and client state, not from interface number alone. Explain findings and the intended change to the user.

### 2. Prepare a reversible patch

Run the patcher without `--apply`:

```bash
python3 scripts/patch_clash_verge.py
```

It locates the active profile merge, plans these changes, and prints no secrets:

- Set `enable_system_proxy: false`.
- Set DNS `enhanced-mode: redir-host` in the persistent merge and generated configs.
- Leave TUN enabled.
- Leave company routes and DNS client configuration untouched.

If auto-detection cannot locate the active merge, pass it explicitly:

```bash
python3 scripts/patch_clash_verge.py --merge-file profiles/EXAMPLE.yaml
```

### 3. Confirm and apply

After the user confirms the specific network changes, run:

```bash
python3 scripts/patch_clash_verge.py --apply
```

The script creates a timestamped backup and reports its path. Then disable macOS HTTP, HTTPS, and SOCKS proxy states for the active network service. Discover the service name rather than assuming `Wi-Fi`:

```bash
networksetup -setwebproxystate "<service>" off
networksetup -setsecurewebproxystate "<service>" off
networksetup -setsocksfirewallproxystate "<service>" off
```

Reload Clash through its local controller or restart Clash Verge Rev. For the standard Unix controller:

```bash
curl --unix-socket /tmp/verge/verge-mihomo.sock \
  -X PUT 'http://localhost/configs?force=true' \
  -H 'Content-Type: application/json' \
  --data '{"path":"<absolute-path-to-clash-verge.yaml>"}'
```

Use elevated execution only when required by the host. Do not weaken permissions to avoid an approval prompt.

### 4. Verify

Verify each layer independently:

```bash
scutil --proxy
scutil --dns
netstat -rn -f inet
ping -c 2 1.1.1.1
ping -c 2 www.apple.com
curl -I --max-time 10 https://www.apple.com
curl -I --max-time 10 https://www.google.com
```

Success requires:

- HTTP, HTTPS, and SOCKS system proxy flags are disabled.
- Clash TUN remains active.
- Company-specific routes still point to the company tunnel.
- Ordinary domains resolve to real addresses, not the conflicting Fake-IP pool.
- HTTPS completes certificate validation. Any HTTP status is transport success only if TLS validation succeeded.
- A public site that needs the personal VPN remains reachable.
- When the user supplies a safe company test hostname, it remains reachable through the company VPN.

Do not claim company application access was verified unless an actual company hostname or service was tested.

### 5. Roll back if verification fails

Use the backup path printed during apply:

```bash
python3 scripts/patch_clash_verge.py --rollback '<backup-directory>'
```

Restore the prior macOS proxy state if it was previously enabled, then reload Clash. Re-run the inspection script.

## Troubleshooting

Read [references/troubleshooting.md](references/troubleshooting.md) only when verification fails or the topology differs from the common two-VPN case.
