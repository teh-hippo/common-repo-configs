# common-repo-configs

Shared configuration presets used across `teh-hippo`'s repositories. Centralising this here keeps every repo's policy identical and lets changes propagate via a single PR.

## Renovate

Each managed repository extends one slot preset from this repo. The slot preset only sets `schedule`; all rules live in the base `renovate/default.json5`.

### Per-repo file

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>teh-hippo/common-repo-configs//renovate/slots/<slot>.json5"]
}
```

### Slot allocation

Routine PRs are staggered across Mon/Tue/Wed mornings so concurrent CI bursts stay well under GitHub Actions concurrency limits. Vulnerability PRs ignore the schedule and run immediately.

| Repository | Slot |
| --- | --- |
| dwerty | `slots/mon-0700.json5` |
| foxess-ha | `slots/mon-0800.json5` |
| ha-govee-led-ble | `slots/mon-0900.json5` |
| ha-home-rules | `slots/tue-0700.json5` |
| ha-homekit-heatercooler | `slots/tue-0800.json5` |
| ha-porkbun | `slots/tue-0900.json5` |
| ha-suno | `slots/wed-0700.json5` |
| hippobox | `slots/wed-0800.json5` |
| icloud_photos_downloader | `slots/wed-0900.json5` |

### Policy summary

- Built on `config:best-practices`, `:enableVulnerabilityAlertsWithLabel`, `:semanticCommits`, `:rebaseStalePrs`.
- Automerge enabled (Renovate + platform). PRs are gated only by CI.
- Security vulnerabilities are raised immediately, ungrouped, and merged as soon as CI passes.
- Routine updates flow on the repo's assigned slot.
- Forks are processed (`forkProcessing: enabled`).
- Lockfile maintenance is handled automatically (weekly, via `config:best-practices`).
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
    uses: teh-hippo/common-repo-configs/.github/workflows/codeql.yml@<sha>  # main
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
- Rust is not supported by CodeQL; hippobox uses `Cargo Audit` instead.

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

### Semantic commit policy

| Source | Commit type | Triggers a release? |
| --- | --- | --- |
| Runtime dep update (`dependencies`, `peerDependencies`, etc.) | `fix(deps)` | Yes |
| Home Assistant `manifest.json` requirement update | `fix(deps)` | Yes |
| Dev/test/build tooling update | `chore(deps)` | No |
| GitHub Actions update | `chore(deps)` | No |
| Vulnerability fix in a runtime dep | `fix(deps)` | Yes |
| Vulnerability fix in a dev dep or Action | `chore(deps)` | No (merge is the fix) |
