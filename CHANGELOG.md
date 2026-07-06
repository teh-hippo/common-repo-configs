# Changelog

## [3.0.0](https://github.com/teh-hippo/common-repo-configs/compare/v2.0.3...v3.0.0) (2026-07-06)


### ⚠ BREAKING CHANGES

* the reusable .github/workflows/codeql.yml has been removed. Repositories should enable code scanning default setup instead of calling it.

### Features

* replace reusable CodeQL workflow with code scanning default setup ([72422dd](https://github.com/teh-hippo/common-repo-configs/commit/72422dd4cfc4ba4c0cabc8c108a0f690facc1dac))

## [2.0.3](https://github.com/teh-hippo/common-repo-configs/compare/v2.0.2...v2.0.3) (2026-07-06)


### Bug Fixes

* bound reusable workflows with generous timeouts ([fc4083a](https://github.com/teh-hippo/common-repo-configs/commit/fc4083adcac89214588aa5cf01a531bbd624dcc1))

## [2.0.2](https://github.com/teh-hippo/common-repo-configs/compare/v2.0.1...v2.0.2) (2026-07-06)


### Bug Fixes

* **mdbook:** retry the Pages deploy once on a transient backend failure ([dd07c10](https://github.com/teh-hippo/common-repo-configs/commit/dd07c1098951f8a9d057d183300fbc7446888929))

## [2.0.1](https://github.com/teh-hippo/common-repo-configs/compare/v2.0.0...v2.0.1) (2026-07-06)


### Bug Fixes

* **release-please:** parse release PR number without fromJSON in env ([0f8773a](https://github.com/teh-hippo/common-repo-configs/commit/0f8773a9aa5b1befaab954b51df6a9d541215d24))
