#!/bin/bash

# Read-only diagnostics for Clash Verge Rev + corporate VPN coexistence.
# Intentionally avoids printing subscription URLs, node definitions, or secrets.

set -u

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Unsupported OS: this diagnostic targets macOS."
  exit 2
fi

config_root="${1:-$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev}"

echo "== Default route =="
route -n get default 2>&1 | awk '/gateway:|interface:/' || true

echo "== Active IPv4 interfaces =="
ifconfig 2>/dev/null | awk '
  /^[a-zA-Z0-9]/ { iface=$1; sub(":$", "", iface) }
  /status: active/ { active[iface]=1 }
  /inet / && $2 != "127.0.0.1" { ip[iface]=$2 }
  END { for (i in active) printf "%s ip=%s\n", i, (i in ip ? ip[i] : "none") }
' | sort

echo "== System proxy flags =="
scutil --proxy 2>&1 | awk '/HTTPEnable|HTTPSEnable|SOCKSEnable|ProxyAutoConfigEnable/' || true

echo "== DNS servers =="
scutil --dns 2>&1 | awk '/nameserver\[[0-9]+\]/ {print $3}' | sort -u || true

echo "== IPv4 route ownership summary =="
netstat -rn -f inet 2>/dev/null | awk '
  $1 == "default" { print "default -> " $NF }
  $NF ~ /^utun[0-9]+$/ { count[$NF]++ }
  END { for (i in count) print i " routes=" count[i] }
' | sort

echo "== Potential 198.18.0.0/15 overlap =="
netstat -rn -f inet 2>/dev/null | awk '$1 ~ /^198\.18/ {print}' || true

echo "== Clash relevant settings =="
for file in "$config_root/verge.yaml" "$config_root/clash-verge.yaml" "$config_root/dns_config.yaml"; do
  if [[ -f "$file" ]]; then
    echo "-- $(basename "$file")"
    awk '/^[[:space:]]*(enable_tun_mode|enable_system_proxy|enhanced-mode|fake-ip-range):/ {print}' "$file"
  fi
done

if [[ ! -d "$config_root" ]]; then
  echo "Clash Verge Rev config directory not found: $config_root"
fi
