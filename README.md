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
- No lockfile maintenance.
- No artificial grouping. Each dep gets its own PR so a single failing dep cannot block others.

### Semantic commit policy

| Source | Commit type | Triggers a release? |
| --- | --- | --- |
| Runtime dep update (`dependencies`, `peerDependencies`, etc.) | `fix(deps)` | Yes |
| Home Assistant `manifest.json` requirement update | `fix(deps)` | Yes |
| Dev/test/build tooling update | `chore(deps)` | No |
| GitHub Actions update | `chore(deps)` | No |
| Vulnerability fix in a runtime dep | `fix(deps)` | Yes |
| Vulnerability fix in a dev dep or Action | `chore(deps)` | No (merge is the fix) |
