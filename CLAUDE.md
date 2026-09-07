# CLAUDE.md

## Purpose

This file contains shared instructions for Claude Code when working on this repository.

Treat it as shared working memory for the development team.

It should capture instructions that affect how Claude should work on this project, so that useful guidance given by one team member can carry across future sessions and other team members.

Do not use this file for:
- app design decisions
- visual or UX preferences
- feature ideas
- temporary implementation details
- general project documentation
- changelog information
- conversational notes

## Shared memory

When a user gives Claude an instruction that changes how Claude should work on this project, consider whether it would be useful for other team members or future sessions to know.

Examples include instructions such as:
- "do it this way"
- "from now on, use this approach"
- "don't do this anymore"
- "when this happens, handle it like this"
- corrections to Claude's usual way of working
- preferences about how Claude should inspect, edit, test, explain, commit, or review work

If the instruction is likely to affect future work, update CLAUDE.md automatically.

The instruction does not need to be permanent. This file should evolve as the team's working practices evolve.

Keep additions concise and place them in the most relevant section.

If a newer instruction conflicts with an older instruction:
- follow the newer instruction
- update CLAUDE.md so it reflects the current team preference
- remove or revise the outdated instruction
- do not leave contradictory guidance in the file

Do not add:
- purely one-off task details
- app design decisions
- visual or UX preferences
- feature ideas
- speculative suggestions
- conversational filler
- information that is only relevant to the current session

## Git workflow

Before making code changes:
1. Run `git status`.
2. Confirm the working tree is in the expected state.
3. Run `git pull`.
4. If there are uncommitted changes, merge conflicts, or anything unexpected, stop and explain the situation before proceeding.

When committing:
- Review the changes before committing.
- Use a clear commit message that describes what changed.
- Avoid vague commit messages.
- Keep unrelated changes out of the same commit where practical.

Before pushing:
- Check whether the remote repository has changed.
- Do not overwrite or discard another team member's work.
- If there is a merge conflict, explain it clearly before resolving it.
- Do not force-push unless explicitly instructed to do so.

This machine has no `gh` CLI, so use plain `git`. Pull requests are not part of the
workflow; work goes to `master`.

Write commit messages in the imperative, describing the behaviour that changed in the
project's own terms ("Stop reading a bed's shape as proof it is fixed"), not the files
that were touched.

When a piece of work is finished and verified — the tests pass, or the adapter has been
run against the real source — commit and push it without asking first. Only pause for
the actions listed under Safety.

## Team working style

This repository is worked on by multiple team members, often using Claude Code.

Assume that another team member may have changed the repository since the last session.

Do not rely on assumptions about the current state of the codebase when it can be checked directly.

Before making significant changes:
- inspect the existing code
- understand the current implementation
- follow established patterns where practical
- avoid unnecessary rewrites
- prefer the smallest safe change that achieves the requested outcome

When a user corrects Claude's approach, treat that correction as potentially useful shared guidance and consider whether CLAUDE.md should be updated.

### Asking the user

Do not put judgement calls to the user as batteries of `AskUserQuestion` options,
including at a skill's checkpoint. Survey the evidence, then set out the decision and a
recommendation in prose and act on it — they can redirect if the recommendation is
wrong. If you need a fact only they hold, ask for it in prose.

### Where the domain rules live

The data rules that hold for every manufacturer — which of two published figures to
record, how to classify a body type, what counts as a travel seat — live in
`docs/adapters/README.md`. Read that file before writing or changing an adapter, and put
any new cross-manufacturer rule there rather than in one brand's notes or in this file.
Do not re-decide a settled rule per manufacturer, and do not re-derive one from the FMLV
baseline export: the baseline still contains the errors those rules exist to correct.

Check the exported data before trusting prose about it. The FMLV field guide is written
for the person typing a row in, so wording such as "select one" is advice to them rather
than a constraint the data obeys — query the export to find out how a group of columns is
actually used.

### Reporting what a run found

Sanity-check pipeline output before presenting it. An implausible number of new products
almost always means a manufacturer has renamed something, so check the claimed-new
products against the ones that disappeared before reporting them as new.

## Environment and the review loop

Development happens on a Windows laptop without local administrator rights — IT
intercepts UAC elevation — so prefer routes that do not need elevation, and do not
propose steps that require it.

Reviewers see this work on the deployed VM, which has its own run store and its own copy
of the code. A local fix is not visible to them until it is deployed, so say that when
handing work over rather than implying the change is already live.

## Safety

Prefer local and reversible changes.

Ask before performing destructive or difficult-to-reverse actions, including:
- force-pushing
- resetting committed work
- deleting branches
- deleting important files
- changing shared infrastructure
- making irreversible data changes

Do not overwrite another team member's work without explicit confirmation.

## Scope of this file

Keep CLAUDE.md useful and reasonably concise.

It should contain guidance about how Claude should work, not what the product should be.

A useful rule of thumb:

- if the instruction changes how Claude should approach the work, it may belong here
- if the instruction changes what the app should look like or do, it usually does not belong here

Regularly revise or remove outdated guidance so the file reflects the team's current way of working.
