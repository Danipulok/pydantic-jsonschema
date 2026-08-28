#!/bin/sh
# Frozen CVE gate over the locked dependency graph (`uv.lock`) — the single home
# of the scan flags and the pinned vulnerability DB, invoked by BOTH the CI
# `Audit` job and the local `just scan-deps` recipe, so local and CI runs execute
# the identical scan and can never disagree just because they ran on different
# days.
#
# Usage: scripts/trivy_scan.sh fs
#
# Reproducibility is the whole point: `TRIVY_DB_REPOSITORY` pins the vulnerability
# DB by digest, so a freshly published advisory can no longer turn a green commit
# red with no code change. The weekly floating rescan re-invokes this same script
# with `TRIVY_DB_REPOSITORY` overridden to the unpinned `:2` tag, surfacing new
# advisories on a controlled cadence instead of at random.
#
# Accepted findings that cannot be fixed yet live in `.trivyignore.yaml`, each
# scoped to its package and carrying an `expired_at` date so a suppression cannot
# rot silently.
set -eu

MODE="${1:?usage: trivy_scan.sh fs}"
if [ "$MODE" != "fs" ]; then
    echo "usage: trivy_scan.sh fs" >&2
    exit 2
fi

# The pinned vulnerability DB. A digest — not a floating tag — is what makes the
# gate reproducible; bumping it is a deliberate, reviewable change. Overridable
# via the environment so the weekly floating rescan can point at the unpinned
# `:2` tag. Kept here rather than in the workflow so CI and `just scan-deps` share
# one source of truth for the pin.
TRIVY_DB_REPOSITORY="${TRIVY_DB_REPOSITORY:-ghcr.io/aquasecurity/trivy-db:2@sha256:620c338424c30aa0141ccec1b5791aec4e1cc2559b26d9bfe8af6238aa1ab5c0}"

# Pinned trivy image for the local/CI docker fallback below. Digest-pinned for
# the same reproducibility reason as the DB.
TRIVY_IMAGE="aquasec/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969"

# MEDIUM included deliberately: the scan runs `--ignore-unfixed`, so the gate is
# already bounded to findings that HAVE a fix (i.e. ones we can act on by bumping
# the dependency), and the `.trivyignore.yaml` ledger absorbs the few whose fix
# cannot be adopted immediately.
TRIVY_SEVERITY="${TRIVY_SEVERITY:-MEDIUM,HIGH,CRITICAL}"

# trivy auto-discovers only the legacy plain `.trivyignore`, never the structured
# YAML form, so the ledger has to be named explicitly. Left unnamed it does not
# error — it simply stops suppressing, turning every accepted finding back into a
# gate failure.
TRIVY_IGNOREFILE="${TRIVY_IGNOREFILE:-.trivyignore.yaml}"

export TRIVY_DB_REPOSITORY TRIVY_SEVERITY TRIVY_IGNOREFILE

# Everything below assumes the repo root as cwd (`uv.lock` and `.trivyignore.yaml`
# lookup). The script `cd`s here on both the host and the container re-exec.
cd "$(dirname "$0")/.."

# CI runners and local machines have no `trivy` binary — re-exec inside the pinned
# image. The exported `TRIVY_*` vars cross the boundary so the in-container run
# uses the identical flags, DB pin and ignorefile. Inside the container `trivy` is
# on `PATH`, so this branch is not re-entered.
if ! command -v trivy >/dev/null 2>&1; then
    exec docker run --rm \
        -v "$PWD:/repo" \
        -v pydantic_jsonschema_trivy_cache:/root/.cache/trivy \
        -w /repo \
        -e TRIVY_DB_REPOSITORY \
        -e TRIVY_SEVERITY \
        -e TRIVY_IGNOREFILE \
        --entrypoint sh \
        "$TRIVY_IMAGE" \
        scripts/trivy_scan.sh "$MODE"
fi

# NOTE: trivy reuses a cached DB purely on age — it records no provenance
# (`db/metadata.json` holds only `Version`/`UpdatedAt`/`NextUpdate`/
# `DownloadedAt`), so a cache populated under a DIFFERENT `TRIVY_DB_REPOSITORY`
# (e.g. the weekly floating rescan's unpinned DB) is served without complaint,
# silently defeating the pin. Guard with a marker file: when the requested
# repository changes, drop the DB (`--vuln-db` removes `db/` only; the scan cache
# survives) and record the new one.
#
# Reproduce (warm cache + a nonexistent digest -> exits 0, downloads nothing; the
# same command on a cold cache dies with MANIFEST_UNKNOWN):
#   docker run --rm -v pydantic_jsonschema_trivy_cache:/root/.cache/trivy \
#     --entrypoint trivy aquasec/trivy:0.72.0 image --download-db-only \
#     --db-repository ghcr.io/aquasecurity/trivy-db:2@sha256:$(printf '0%.0s' $(seq 64))
trivy_cache_dir="${TRIVY_CACHE_DIR:-${HOME:-/root}/.cache/trivy}"
db_ref_marker="$trivy_cache_dir/.db-repository"
if [ "$(cat "$db_ref_marker" 2>/dev/null || true)" != "$TRIVY_DB_REPOSITORY" ]; then
    # Fail closed: the marker is written ONLY after a successful purge. If `trivy clean`
    # is swallowed (e.g. `|| true`) and the marker is written anyway, the next run sees
    # marker == requested repo, skips the purge, and serves the STALE DB under the new
    # pin — silently defeating the reproducibility the pin exists to guarantee. `set -e`
    # aborts the run on a nonzero `trivy clean`, leaving the marker unchanged so the
    # purge is retried next time. `trivy clean --vuln-db` exits 0 on an empty cache, so
    # the first run is unaffected.
    trivy clean --vuln-db >/dev/null
    mkdir -p "$trivy_cache_dir"
    printf '%s\n' "$TRIVY_DB_REPOSITORY" >"$db_ref_marker"
fi

# `--include-dev-deps`: match the coverage of the `uv audit` this replaces — gate
# dev/test/docs dependencies too, not just runtime. The advisory that motivated
# freezing the DB (`pymdown-extensions`, GHSA-9xwg-3r6f-jcx2) was a docs-group
# dep, which trivy suppresses by default.
trivy fs \
    --scanners vuln \
    --severity "$TRIVY_SEVERITY" \
    --ignore-unfixed \
    --include-dev-deps \
    --exit-code 1 \
    uv.lock
