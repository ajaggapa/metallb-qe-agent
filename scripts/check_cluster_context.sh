#!/usr/bin/env bash
# Verify OpenShift/Kubernetes CLI access using the user's kubeconfig.
# Usage:
#   export KUBECONFIG=/path/to/kubeconfig
#   scripts/check_cluster_context.sh
# Or:
#   scripts/check_cluster_context.sh /path/to/kubeconfig
set -euo pipefail

if [[ $# -ge 1 ]]; then
  export KUBECONFIG="$1"
fi

if [[ -z "${KUBECONFIG:-}" ]]; then
  echo "ERROR: KUBECONFIG is not set and no path was passed as the first argument." >&2
  echo "Example: export KUBECONFIG=~/kubeconfigs/dev && $0" >&2
  exit 2
fi

if [[ ! -f "$KUBECONFIG" ]]; then
  echo "ERROR: KUBECONFIG file not found: $KUBECONFIG" >&2
  exit 2
fi

if ! command -v oc >/dev/null 2>&1; then
  echo "ERROR: oc is not on PATH." >&2
  exit 2
fi

echo "Using KUBECONFIG=$KUBECONFIG"
oc whoami
oc cluster-info 2>/dev/null || true
echo "OK: cluster context is reachable."
