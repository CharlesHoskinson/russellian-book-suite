# Change: repo-hygiene-graphify

## Why

The repository accumulated dozens of stale remote branches and had no committed
operator convention for keeping the graphify map focused on live code. That made
branch state harder to reason about and made graph-guided orientation noisier
than it needed to be.

## What

- Retire non-main remote branches, preserving unmerged tips as archive tags.
- Add graphify extraction scope rules so local code maps emphasize source, CI,
  and operator docs rather than historical artifacts.
- Document branch hygiene and graphify map regeneration/query commands.

## Out of scope

- Rewriting CI workflows.
- Committing `graphify-out/` artifacts.
- Restoring or merging archived branch work.
