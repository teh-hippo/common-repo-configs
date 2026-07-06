# common-repo-configs

Shared configuration presets used across `teh-hippo`'s repositories. Centralising this here keeps every repo's policy identical and lets changes propagate via a single PR.

## Renovate

Each managed repository extends the base preset directly. All rules live in `renovate/default.json5`.

### Per-repo file

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>teh-hippo/common-repo-configs//renovate/default.json5"]
}
```

### Policy summary

- Built on `config:best-practices`, `:enableVulnerabilityAlertsWithLabel`, `:semanticCommits`, `:rebaseStalePrs`.
- Automerge enabled (Renovate + platform). PRs are gated only by CI.
- Security vulnerabilities are raised immediately, ungrouped, and merged as soon as CI passes.
- Routine updates flow continuously and auto-merge on green CI.
- Forks are processed (`forkProcessing: enabled`).
- Lockfile maintenance runs daily and auto-merges — the autonomous path that clears transitive-only (lockfile) CVEs.
- No artificial grouping. Each dep gets its own PR so a single failing dep cannot block others.
- OSV vulnerability alerts enabled to broaden coverage beyond GHSA.
- 3-day release-age soak on routine updates (mitigates supply-chain attacks and quickly-unpublished releases). Vulnerability PRs bypass the soak.
- Dependency Dashboard issue disabled. Config errors surface via the Mend web UI.
- Automerge strategy is left to the repo default (every managed repo is rebase-only).

## CodeQL

A reusable workflow at `.github/workflows/codeql.yml` provides the shared analysis job. Each consuming repo has a thin caller workflow that sets triggers and language. Updates to analysis steps propagate via a single PR here.

### Per-repo caller

```yaml
name: CodeQL
on:
  push:
    branches: [<default>]
  schedule:
    - cron: "0 14 * * <day>"
jobs:
  analyze:
    uses: teh-hippo/common-repo-configs/.github/workflows/codeql.yml@<sha>  # v1
    permissions:
      contents: read
      security-events: write
    with:
      language: python   # or c-cpp for compiled, javascript, etc.
      # build-mode: none  # default
```

### Policy

- `push:` scoped to default branch only. Renovate branch pushes do not trigger a scan; the post-merge push scan covers them.
- `pull_request:` not used. These repos receive effectively no external contributor traffic.
- `schedule:` retained as the only mechanism that re-runs CodeQL's evolving query set against already-merged code.
- Status check name (`analyze / Analyze`) is not required by any repo's branch protection.
- Rust is not supported by CodeQL; Rust repos use the shared **Security Audit** workflow (`cargo audit`, see below) instead.

### Weekly schedule allocation

Distributed across the week at 14:00 UTC (midnight Sydney AEDT, off-peak) so concurrent Actions usage stays low. CodeQL has no downstream pipeline, so collisions only cost concurrent minutes.

| Day (UTC) | Time | Repo |
| --- | --- | --- |
| Mon | 14:00 | dwerty |
| Tue | 14:00 | ha-govee-led-ble |
| Wed | 14:00 | foxess-ha |
| Thu | 14:00 | ha-home-rules |
| Fri | 14:00 | ha-homekit-heatercooler |
| Sat | 14:00 | ha-porkbun |
| Sun | 14:00 | ha-suno |
| Mon | 18:00 | icloud_photos_downloader |
| Tue | 18:00 | teamdeck |

### Semantic commit policy

| Source | Commit type | Triggers a release? |
| --- | --- | --- |
| Runtime dep update (`dependencies`, `peerDependencies`, etc.) | `fix(deps)` | Yes |
| Home Assistant `manifest.json` requirement update | `fix(deps)` | Yes |
| Dev/test/build tooling update | `chore(deps)` | No |
| GitHub Actions update | `chore(deps)` | No |
| Vulnerability fix in a runtime dep | `fix(deps)` | Yes |
| Vulnerability fix in a dev dep or Action | `chore(deps)` | No (merge is the fix) |

## Reusable workflows

Beyond CodeQL, two shared `workflow_call` workflows let multiple repos run identical
release and audit jobs. Each consuming repo keeps its own config and triggers; the
shared workflow holds the steps.

### Versioning / pinning

This repo is tagged `v1` (a moving major tag). Callers pin the underlying commit with the
tag in a trailing comment, e.g. `@<sha>  # v1`, so Renovate's github-actions manager can
advance the SHA when `v1` moves. A bare `@main` pin is **not** Renovate-trackable, so avoid
it for reusable-workflow calls.

### `release-please.yml`

Runs [release-please](https://github.com/googleapis/release-please) and auto-merges the
release PR. All semantics come from the consuming repo's `release-please-config.json` and
`.release-please-manifest.json`.

```yaml
name: Release Please
on:
  push:
    branches: [<default>]
jobs:
  release-please:
    uses: teh-hippo/common-repo-configs/.github/workflows/release-please.yml@<sha>  # v1
    secrets:
      RELEASE_TOKEN: ${{ secrets.RELEASE_TOKEN }}
```

Prerequisites in the consuming repo:

- A `RELEASE_TOKEN` repo secret holding a PAT with **Contents: read/write** and
  **Pull requests: read/write**. A PAT (not the default `GITHUB_TOKEN`) is required so the
  release tag triggers the repo's downstream release workflow.
- For the auto-merge step to succeed, enable **Allow auto-merge** in repo settings and add a
  ruleset/branch protection on the default branch with at least one required status check
  (auto-merge needs something to wait on).

### `security-audit.yml`

Runs `cargo audit` (via `rustsec/audit-check`) and opens a GitHub issue when an advisory is
found. Pass `working-directory` when the crate is not at the repo root.

```yaml
name: Security Audit
on:
  push:
    branches: [<default>]
    paths: ["<crate-dir>/**"]
  schedule:
    - cron: "0 6 * * 1"
jobs:
  audit:
    uses: teh-hippo/common-repo-configs/.github/workflows/security-audit.yml@<sha>  # v1
    permissions:
      contents: read
      issues: write
      checks: write
    with:
      working-directory: <crate-dir>   # omit for a crate at the repo root
```

### `mdbook.yml`

Builds an [mdBook](https://rust-lang.github.io/mdBook/) and deploys it to GitHub Pages. The
consuming repo owns its triggers and grants the Pages permissions; the shared workflow
installs mdBook, runs `mdbook build`, and publishes the result. Set `path` when `book.toml`
is not at the repo root.

| Input | Default | Description |
| --- | --- | --- |
| `path` | `.` | Directory containing `book.toml`. The built site is taken from `<path>/book`. |

```yaml
name: Docs
on:
  push:
    branches: [<default>]
    paths:
      - "docs/**"
      - ".github/workflows/docs.yml"
  workflow_dispatch:
jobs:
  docs:
    uses: teh-hippo/common-repo-configs/.github/workflows/mdbook.yml@<sha>  # v1
    permissions:
      pages: write
      id-token: write
      contents: read
    with:
      path: docs
```

Prerequisite in the consuming repo:

- Set **Settings > Pages > Build and deployment > Source** to **GitHub Actions**. Without
  this the deploy step cannot publish.

### `rust-release.yml`

Builds cross-platform release binaries, attaches them to the tag's GitHub release with
SHA-256 checksums and build provenance, and optionally publishes crates to crates.io. The
consuming repo triggers it on a version tag and grants the release and OIDC permissions; the
target list, binary name, and crate publish order arrive as inputs. Publishing uses the
crates.io Trusted Publisher flow, so no registry token is stored.

| Input | Default | Description |
| --- | --- | --- |
| `binary-name` | (required) | Binary to build and package. Passed to `cargo --bin`, so a package name that differs from the binary still works. |
| `targets` | `["x86_64-unknown-linux-musl","aarch64-unknown-linux-musl","x86_64-pc-windows-gnu"]` | JSON-array string of target triples for the build matrix. `aarch64` targets build with `cross`. |
| `publish-crates` | `[]` | JSON-array string of crate names to `cargo publish` in order (dependencies first). The empty array skips publishing. |
| `archive-prefix` | `""` | Archive filename prefix. Falls back to `binary-name` when empty. |

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    uses: teh-hippo/common-repo-configs/.github/workflows/rust-release.yml@<sha>  # v1
    permissions:
      contents: write
      id-token: write
      attestations: write
    with:
      binary-name: <bin>
      publish-crates: '["crate-a","crate-b"]'   # omit to build binaries only
```

Prerequisites in the consuming repo:

- The tag (for example `v1.2.3`) must match the first `version` in `Cargo.toml`; the build
  fails fast on a mismatch.
- To publish, configure a crates.io **Trusted Publisher** for each crate whose OIDC
  `job_workflow_ref` matches this reusable workflow
  (`teh-hippo/common-repo-configs/.github/workflows/rust-release.yml@<ref>`) with the
  environment set to `crates-io`. Leave `publish-crates` as `[]` to build binaries only.

