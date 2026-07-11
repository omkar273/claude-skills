---
name: manage-skills
description: Use when adding a new skill to this repo, refreshing a vendored or mine skill from its source, or regenerating the skill catalog in README.md.
---

# Managing This Skills Repo

This repo holds two kinds of skills under `skills/`, distinguished by each skill's `.origin.yaml`, not by folder location (the directory stays flat so the repo works as an installable Claude Code plugin):

- **mine** — skills authored directly in this repo, or snapshotted from a repo the user owns.
- **vendored** — third-party skills snapshotted in for reference and use.

Three scripts under `scripts/` handle the mechanical parts. Run them from the repo root.

## Add a new skill

```
python3 skills/manage-skills/scripts/new_skill.py <name> --origin mine|vendored \
  [--source-repo REPO] [--source-path PATH] [--source-ref REF] [--seed-from DIR]
```

- Without `--seed-from`: scaffolds `skills/<name>/SKILL.md` as a TODO stub — use this for a skill you're about to write from scratch.
- With `--seed-from DIR`: copies `DIR`'s full contents (it must already contain a `SKILL.md`) into `skills/<name>/` — use this to adopt an existing skill, whether one you wrote elsewhere or a third-party one you're vendoring in.
- `--source-repo` defaults to `local`, meaning "no separate repo tracks this content" (nothing to sync from later). Set it to a git URL or a local path to an existing checkout when there IS a canonical upstream, so `sync_skill.py` can refresh from it later.

After adding a skill, run `gen_catalog.py` (below) to refresh `README.md`.

## Refresh a skill from its source

```
python3 skills/manage-skills/scripts/sync_skill.py <name>
python3 skills/manage-skills/scripts/sync_skill.py --all
```

Reads the skill's `.origin.yaml`. If `source_repo` is `local`, there's nothing to sync (this repo IS the only copy) and the script says so and exits. Otherwise it re-copies from the recorded local path, or shallow-clones the recorded URL into a scratch directory first, then updates `source_ref`/`snapshotted_at`.

## Regenerate the catalog

```
python3 skills/manage-skills/scripts/gen_catalog.py
```

Rebuilds the table between the `<!-- CATALOG:START -->`/`<!-- CATALOG:END -->` markers in `README.md` from every skill's `SKILL.md` frontmatter and `.origin.yaml`. Safe to run any time; never edit that table by hand since it will be overwritten.

## Writing or improving a skill's content

This skill only handles repo mechanics (scaffolding, syncing, cataloging). For guidance on structuring a skill well — tight descriptions, when to trigger, avoiding bloat — use the vendored `writing-skills` skill instead of duplicating that guidance here.
