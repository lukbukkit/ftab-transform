# Sample Plugin
Author: **Vector 35 Inc**

_This is a short description meant to fit on one line._

## Description:
This is a longer description meant for a sample plugin that demonstrates the metadata format for Binary Ninja plugins. Note that the [community-plugins repo](https://github.com/Vector35/community-plugins) contains a useful [utility](https://github.com/Vector35/community-plugins/blob/master/generate_plugininfo.py) to validate the plugin.json. Additionally, the [release helper](https://github.com/Vector35/release_helper) plugin is helpful for more easily pushing new releases, incrementing versions, and creating the appropriate GitHub tags.

Note that originally we recommended specifying the contents of this entire file inside of the [plugin.json](./plugin.json) but the latest repository generator will use the readme contents directly which means you should simply leave an empty longdescription field. 

## Cutting a release

This repo includes a [release workflow](./.github/workflows/release.yml) that you are welcome to copy into your own plugin repo (it works unmodified as long as `plugin.json` is at the repository root).

To release: **Actions → Release → Run workflow**. Leave the version box empty to bump the last number of the current version (1.3.5 → 1.3.6), or type an explicit version such as `2.0.0`. From the command line, `gh workflow run release.yml` (add `-f version=2.0.0` for an explicit version).

The workflow bumps `version` in `plugin.json`, commits and pushes that change to the default branch, tags **that** commit, and creates the release from the tag — in that order. This matters because [extensions.binary.ninja](https://extensions.binary.ninja) reads `plugin.json` from the commit your latest release's tag points at, and the `version` field in that file is the only version it looks at. The tag name and release title are never parsed. If that version string matches a version the server already has, your release is silently skipped and the code never reaches users. The workflow refuses to release a version that is malformed, already tagged, already published, or not greater than the current one.

The workflow is also permissive in what it reads and strict in what it writes. It accepts and repairs the manifest problems that quietly break ingestion — a trailing comma, a UTF-8 BOM, legacy `{"plugin": {...}}` nesting, a camelCase `minimumBinaryNinjaVersion`, a missing `pluginmetadataversion`, a `v` prefix or a bare major version — then writes `plugin.json` back in canonical form and reports everything it changed in the job log and the run summary. It refuses to release at all if a field the server requires (`name`, `api`, `description`, `license`, `version`, `author`) is missing.

Versions are written as `MAJOR.MINOR` or `MAJOR.MINOR.PATCH`: digits only, no leading `v`, no leading zeros, no suffix, and 16 characters or fewer. That is the intersection of the two version rules the server applies, so anything else (`1.0.0-beta`, `2023.1.1.4`) either cannot be parsed or cannot be stored.

Your versioning scheme is preserved rather than normalized to three components — a plugin on `1.3` releases `1.4` next, not `1.4.0`. The one exception is a bare major version, which the server's validator rejects, so `7` becomes `8.0`. Versions are still *compared* numerically, so `1.4` and `1.4.0` count as the same release and cannot both be published.

## License

This plugin is released under an [MIT license](./license).
