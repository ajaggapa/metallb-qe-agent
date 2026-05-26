#!/usr/bin/env bash
# Resolve the gitignored directory for agent-generated transient files.
# Override with METALLB_AGENT_TMP_DIR if needed.

metallb_agent_tmp_dir() {
  local root_dir="${1:?root_dir required}"
  local dir="${METALLB_AGENT_TMP_DIR:-${root_dir}/.cursor/workspaces/agent-tmp}"
  mkdir -p "${dir}"
  printf '%s\n' "${dir}"
}
