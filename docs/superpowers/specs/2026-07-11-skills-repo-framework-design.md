# Personal Skills Repo — Framework Design

## Purpose

`claude-skills` is a personal, version-controlled library of Claude Code skills. It holds two kinds of skills side by side:

- **mine** — skills the user wrote themselves (e.g. the Flexprice billing skills, currently living in the `flexprice/claude-plugin` repo).
- **vendored** — third-party skills the user relies on but didn't author (e.g. `superpowers` workflow skills, design skills, `graphify`), snapshotted in for a single durable, browsable, editable collection.

The repo starts as a plain, low-friction archive but is laid out so it can become an installable Claude Code plugin (`claude plugin add <repo>`) without restructuring later.

## Repo layout

Every real Claude Code plugin inspected on this machine (superpowers, nx-claude-plugins, the official marketplace — 20+ examples) discovers skills one level deep only: `skills/<skill-name>/SKILL.md`. Plugin discovery does not recurse into subfolders. So the "mine vs. vendored" distinction is **not** expressed as folder nesting — it's metadata. `skills/` stays physically flat for plugin compatibility.

```
claude-skills/
├── .claude-plugin/
│   └── plugin.json              # makes the repo installable: claude plugin add <repo>
├── skills/
│   ├── pricing-setup/            # mine
│   │   ├── SKILL.md
│   │   └── .origin.yaml
│   ├── subscription-import/
│   ├── batch-subscription-draft-compute/
│   ├── batch-invoice-compute/
│   ├── invoice-validation/
│   ├── draft-invoice-recalculate/
│   ├── brainstorming/            # vendored (superpowers)
│   ├── writing-plans/
│   ├── executing-plans/
│   ├── systematic-debugging/
│   ├── test-driven-development/
│   ├── requesting-code-review/
│   ├── receiving-code-review/
│   ├── writing-skills/
│   ├── frontend-design/          # vendored (local design pack)
│   ├── ui-ux-pro-max/
│   ├── graphify/                 # vendored (unknown upstream)
│   └── manage-skills/            # mine — repo tooling (see below)
│       ├── SKILL.md
│       └── scripts/
│           ├── new_skill.py
│           ├── sync_skill.py
│           └── gen_catalog.py
└── README.md                     # generated catalog of all skills
```

## Provenance metadata: `.origin.yaml`

Every skill folder (mine or vendored) carries a small YAML file recording where it came from, kept separate from `SKILL.md`'s frontmatter so Claude Code's own parsing of `SKILL.md` isn't affected by extra fields:

```yaml
origin: mine | vendored
source_repo: https://github.com/flexprice/claude-plugin   # or "local" if no identifiable upstream repo exists
source_path: skills/pricing-setup                          # path within the source repo, if applicable
source_ref: c4cd3f7                                         # commit sha, tag, or version string snapshotted
snapshotted_at: 2026-07-11                                  # YYYY-MM-DD
```

For skills with no discoverable upstream repo (`graphify`, the local design skills), `source_repo` is set to the single sentinel value `local` — meaning "sourced from files already on this machine, no git repo tracks them" — and `source_ref` records whatever version marker is available (e.g. `graphify`'s `.graphify_version` = `0.8.14`, or omitted where there is none). These can be corrected later if a real upstream source turns up.

## Plugin scaffolding

`.claude-plugin/plugin.json` at repo root, following the pattern used by every inspected plugin:

```json
{
  "name": "claude-skills",
  "description": "Personal library of Claude Code skills — self-written and curated third-party.",
  "version": "0.1.0",
  "skills": "./skills/"
}
```

Not registered in any marketplace yet — this only makes the repo installable directly (`claude plugin add <path-or-url>`) if/when desired. `author`/`homepage`/`license` fields can be filled in before any real distribution.

## Initial migration list

**Mine** (snapshotted from `flexprice/claude-plugin`, `skills/` at repo root there):
`pricing-setup`, `subscription-import`, `batch-subscription-draft-compute`, `batch-invoice-compute`, `invoice-validation`, `draft-invoice-recalculate`

**Vendored — superpowers** (snapshotted from the cached `superpowers` plugin, `obra/superpowers`):
`brainstorming`, `writing-plans`, `executing-plans`, `systematic-debugging`, `test-driven-development`, `requesting-code-review`, `receiving-code-review`, `writing-skills`

**Vendored — design** (snapshotted from local `~/.claude/skills`, no upstream repo identified):
`frontend-design`, `ui-ux-pro-max`

**Vendored — other**:
`graphify` (snapshotted from `~/.claude/skills/graphify`, `source_repo: local`, version `0.8.14`)

Deliberately excluded from this first pass (can be added later via `manage-skills`): the more specialized design skills (`design`, `design-system`, `ui-styling`, `banner-design`, `brand`, `slides`), and `dataviz` (no local file source was found for it — likely hosted, not vendorable as-is).

## The `manage-skills` skill

A skill purpose-built for maintaining this repo, backed by scripts rather than freeform instructions so the mechanical parts (scaffolding, syncing, cataloging) are deterministic:

- **`scripts/new_skill.py <name> --origin mine|vendored [--source-repo URL] [--source-path PATH]`** — scaffolds `skills/<name>/SKILL.md` from a minimal template and writes a filled-in `.origin.yaml`. Reminds the user to run the catalog regen afterward.
- **`scripts/sync_skill.py <name|--all>`** — reads `source_repo`/`source_path` from `.origin.yaml`, re-copies the latest files from that source (a local path directly, or a fresh clone into the scratch directory for a remote URL), reports a diff summary, and updates `source_ref`/`snapshotted_at` on success.
- **`scripts/gen_catalog.py`** — regenerates the skill table in `README.md` from every skill's `SKILL.md` frontmatter plus `.origin.yaml`, so the catalog can't drift from what's actually in `skills/`.

`SKILL.md` for `manage-skills` documents when to use each script, and for "help me write or improve a skill" it defers to the vendored `writing-skills` skill for authoring quality (structure, tight descriptions, avoiding bloat) instead of duplicating that guidance.

## README catalog

Single generated table in `README.md`, grouped into "Mine" and "Vendored" sections, columns: Skill | Origin | Description | Source.

## Ongoing workflow

- New self-written skill → `new_skill.py --origin mine`.
- New third-party skill worth keeping → `new_skill.py --origin vendored --source-repo ... --source-path ...`.
- Upstream of a vendored skill changed → `sync_skill.py <name>`.
- Improving any skill's content → invoke `writing-skills` for guidance.
- Every change ends with `gen_catalog.py` to refresh `README.md`, then a commit.
