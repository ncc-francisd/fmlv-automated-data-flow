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