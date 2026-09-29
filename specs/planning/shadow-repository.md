---
type: Plan
status: proposed
---

# Shadow — repository organization proposal

> **Decision executed.** Canonical repository strategy now lives in
> [`shadow-ecosystem/strategy/repository-topology.md`](../../../shadow-ecosystem/strategy/repository-topology.md).
> This proposal remains the historical input that preceded repository creation.
>
> Options updated 2026-09-21 after the owner requested an independent legacy maintenance track.
> The umbrella name **Shadow** is agreed. Repository creation/rename, local moves and package
> renames are **not yet approved**. This remains a proposal, not an execution directive.

## Requirement: two independent delivery tracks

Intent Studio must continue consuming stable `shadow-hdk` releases while the native rewrite is
not ready. Urgent bugs, security fixes and essential generic product-unblocking additions must
be releasable without waiting for native phase completion. Call this **maintenance-supported**,
not deprecated, until a usable replacement and migration path exist.

## Current recommendation: separate repositories during the transition

Keep `shadow-hdk` and its established release pipeline unchanged; create a new `shadow` monorepo
for the Rust foundation and all new first-party SDKs/components/surfaces **if the owner confirms**.
Do not rename the legacy repository during this transition. Naming the new repository `shadow`
would establish the new identity without redirecting current consumers.

This revises the earlier recommendation to rename this repository. A separate repository does
provide a stronger release/configuration boundary; saying it offered no isolation benefit was
too strong. It is not technically required for concurrent work, but is justified here by the
planned Python/LangGraph-to-Rust architectural and distribution change.

| Option | Advantage | Cost / required discipline |
|---|---|---|
| One repository, separate branches and worktrees | Retains one history, issue tracker and administrative setup; urgent stable work can ship independently | Separate stable/native integration and publishing policies; long-lived branch drift; shared repository secrets and workflow settings |
| Legacy `shadow-hdk` plus new `shadow` monorepo | Independent release configuration and native layout; no disruption to the product's existing dependency | Bootstrap CI and ownership again; traceability and deliberate transfer of relevant fixes/contract tests |

The inspected `.github/workflows/publish.yml` runs on `release: published` and manual dispatch,
builds the Python package plus lockstep Linux helper, and has no native/stable release-family
routing. Its version/tag check guards mismatch but is not a dual-track publishing design.
`specs/config.md` also defines one `phase → staging → main` flow. The branch option is viable
but needs explicit workflow and policy changes; merely naming a branch does not isolate releases.

One monorepo still owns the **new** Core, Runtime, schemas, SDKs, components, conformance tests
and first-party surfaces. This is not one repository per language. Intent Studio remains outside
both implementation repositories. Shared ownership does not imply one giant package or binary.

## Transfer and ownership, if the two-repository option is approved

- Create the destination with an explicit visibility/owner decision and check name availability.
  Do not assume it should be public because the current project is public.
- Transfer target architecture, the two diagrams, approved decisions, phase mapping and relevant
  contract fixtures/examples first. Preserve source commit, paths and license/provenance for
  selected reused code such as the Linux helper. Do not blindly copy the entire Python engine.
- Exclude credentials, `.env` files, local stores, virtual environments, build/cache outputs,
  runtime sessions and local tool configuration. Do not blindly enable copied publish workflows.
- Establish separate native-preview artifacts and exactly one publisher per package identity.
  Do not overwrite the stable Python distribution from the new repository. Exact native package
  names require registry availability and compatibility decisions before publication.
- Legacy fixes are reviewed for relevance to native contract fixtures and implementation. No
  blanket Python-to-Rust cherry-picking or permanent bidirectional source synchronization.
- At bootstrap, hand native epic ownership to the destination and leave a source pointer here;
  do not leave the same phase actively owned by two repositories. Until then the current specs
  remain the pending transfer source and Phase 46 must not start in either location.
- Track the migration handoff across repositories if this option is selected; implementation
  phases stay owned by the new repository. Each repository's session owns its own documents.
- Migration, package transition, legacy deprecation and eventual archive require explicit gates.
  Do not archive the old repository merely because the new one exists.

The branch alternative would keep the same two delivery tracks in separate worktrees, retain
stable publication on the legacy line, and isolate native previews before changing the default.
The current architecture does not depend on which repository option is chosen.

## Target layout, not directories created now

```text
shadow/
  crates/             Rust Core, Runtime, native adapters and binding crates
  sdk/
    python/           Python authoring API, native binding integration and client
    typescript/       TypeScript authoring API, client and Node launcher
  apps/
    cli/              Thin command-line composition root
    desktop/          Later, optional
    web/              Later, optional
  components/         Optional implementations requiring their own dependencies
  presets/            Ready-made agents, workflows and harness definitions
  schemas/            Published/generated wire contracts; checked for drift
  tests/conformance/  Shared behavioral fixtures and cross-surface checks
  examples/           Consumers of public APIs, never privileged internal callers
  docs/               User and developer documentation
  specs/              Decisions, architecture, epics, phases and evidence
```

Crate/package names and exact directory moves are derived with their implementation phase. Do
not create empty application projects or move the current Python tree just to match this drawing.
Keep `src/shadow_hdk`, `clients/typescript` and `native/sandbox` buildable until their migration is
tested. A Cargo workspace coordinates native crates; language tooling remains native to its
ecosystem. No extra monorepo orchestrator is required just for having multiple languages.

## Separate four naming decisions

| Item | Current action |
|---|---|
| Product name | Shadow, used in target specs now |
| GitHub repository topology | Recommend legacy `shadow-hdk` plus new `shadow`; owner decision pending |
| Local checkout and saved project paths | Leave unchanged; update separately with coordination |
| Package names, imports and executable names | Preserve existing consumers; decide with availability and compatibility checks |

## Rename checklist, only if the branch-and-rename alternative is selected

1. Check target-name availability, administrative access and consumers of this repository's URLs.
2. Inventory release/publish workflows, package metadata, documentation links, Pages if present,
   reusable actions/workflows, registered projects/worktrees and ecosystem references.
3. Rename the existing GitHub repository; update this checkout's remote after verifying identity.
4. Verify tags, branches, issues, releases, package publication settings and CI references.
5. Coordinate external product/project paths with their owners; never silently edit another repo.
6. Move the local checkout only as a separate deliberate action; avoid breaking active tasks.
7. Preserve old package/import names until their own tested migration. Do not reuse the old GitHub
   repository name, which would invalidate its redirect.

GitHub documents redirects for repository information and Git operations after renaming, but
Pages URLs and calls to an action hosted in the renamed repository need special handling. These
exceptions are why a remote rename is not treated as a blanket string replacement.
[GitHub repository rename documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).
