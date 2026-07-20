# common-repo-configs

Shared configuration presets used across `teh-hippo`'s repositories. Centralising this here keeps every repo's policy identical and lets changes propagate via a single PR.

This repo lints itself (`lint.yml`: actionlint + zizmor; `renovate-validate.yml`: preset validation) and `main` requires the `lint` check. Releases are cut automatically by release-please (`release.yml`) as immutable semver tags — see [Versioning / pinning](#versioning--pinning).

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
- Renovate-managed automerge enabled. Renovate merges on its next hosted run after every PR check passes.
- Security vulnerabilities are raised immediately, ungrouped, and merged as soon as CI passes.
- Routine updates flow continuously and auto-merge on green CI.
- Forks are processed (`forkProcessing: enabled`).
- Lockfile maintenance runs daily and auto-merges — the autonomous path that clears transitive-only (lockfile) CVEs.
- No artificial grouping. Each dep gets its own PR so a single failing dep cannot block others.
- OSV vulnerability alerts enabled to broaden coverage beyond GHSA.
- 3-day release-age soak on routine updates (mitigates supply-chain attacks and quickly-unpublished releases). Vulnerability PRs bypass the soak.
- Pin and digest updates also bypass the soak: they carry no new source, and a rebuilt tag would otherwise re-pin a fresh digest and reset the age clock indefinitely.
- Dependency Dashboard issue disabled. Config errors surface via the Mend web UI.
- Automerge uses each repo's configured merge method (managed repos are rebase-first).

### Semantic commit policy

| Source | Commit type | Triggers a release? |
| --- | --- | --- |
| Runtime dep update (`dependencies`, `peerDependencies`, etc.) | `fix(deps)` | Yes |
| Home Assistant `manifest.json` requirement update | `fix(deps)` | Yes |
| Dev/test/build tooling update | `chore(deps)` | No |
| GitHub Actions update | `chore(deps)` | No |
| Vulnerability fix in a runtime dep | `fix(deps)` | Yes |
| Vulnerability fix in a dev dep or Action | `chore(deps)` | No (merge is the fix) |

## CodeQL

CodeQL runs through GitHub [code scanning default setup](https://docs.github.com/en/code-security/code-scanning/enabling-code-scanning/configuring-default-setup-for-code-scanning), enabled per repository under **Settings > Code security > Code scanning**. There is no workflow file to maintain or pin: GitHub auto-detects the languages (including Actions), runs analysis on push to the default branch and on a weekly schedule, and manages the CodeQL version itself.

Default setup and an advanced CodeQL workflow cannot coexist, so managed repositories carry no `codeql.yml` caller. Rust analysis is included now that CodeQL Rust support is GA.

## Reusable workflows

The shared `workflow_call` workflows below (`release-please`, `security-audit`, `mdbook`, `rust-release`) let repos run identical release, audit, and docs jobs. Each consuming repo keeps its own config and triggers; the shared workflow holds the steps.

## Copilot CLI plugins

### `rust-lsp`

The `plugins/rust-lsp` plugin provides the shared `rust-analyzer` configuration. Enable it in a Rust repository with `.github/copilot/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "teh-hippo": {
      "source": {
        "source": "github",
        "repo": "teh-hippo/common-repo-configs"
      }
    }
  },
  "enabledPlugins": {
    "rust-lsp@teh-hippo": true
  }
}
```

The repository environment must provide `rust-analyzer` on `PATH`.

### Versioning / pinning

Releases are cut by [release-please](https://github.com/googleapis/release-please) as immutable semver tags (`v2.0.0`, `v2.1.0`, …) from the Conventional Commits merged here; the old moving `v1`/`v2` tags are retired. Callers pin the exact commit with the release in a trailing comment, e.g. `@<sha>  # v2.0.2`. Renovate's github-actions manager tracks the release and advances both the SHA and the comment on its own, so a `feat:`/`fix:` merged here reaches consumers as an auto-merged Renovate PR. The SHA-plus-version-comment form is required — a bare `@main` or `@v2` pin defeats SHA-pin enforcement and Renovate tracking.

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
    uses: teh-hippo/common-repo-configs/.github/workflows/release-please.yml@<sha>  # v2.0.2
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

Runs `cargo audit` directly (no third-party action; the `rustsec/audit-check` wrapper kept lagging GitHub's Node-runtime deprecations) and fails the run on an advisory. Pass `working-directory` when the crate is not at the repo root.

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
    uses: teh-hippo/common-repo-configs/.github/workflows/security-audit.yml@<sha>  # v2.0.2
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
    uses: teh-hippo/common-repo-configs/.github/workflows/mdbook.yml@<sha>  # v2.0.2
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
| `targets` | x86_64-linux (musl, cargo), aarch64-linux (musl, cross), x86_64-windows (MSVC, cargo) | JSON-array string consumed as the build matrix. Each entry is an object: `target` (Rust triple), `os` (runner label), `build-tool` (`cargo` or `cross`), `label`, and optional `rustflags`. |
| `publish-crates` | `[]` | JSON-array string of crate names to `cargo publish` in order (dependencies first). The empty array skips publishing. |
| `archive-prefix` | `""` | Archive filename prefix. Falls back to `binary-name` when empty. |

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    uses: teh-hippo/common-repo-configs/.github/workflows/rust-release.yml@<sha>  # v2.0.2
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
