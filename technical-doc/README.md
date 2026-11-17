# Technical docs: start here

Read in this order. Each doc answers one question, and each fact has one source of truth. Other docs link to it instead of repeating it.

| # | Doc | Question it answers | Source of truth for | Status |
| --- | --- | --- | --- | --- |
| 1 | [user-stories.md](./user-stories.md) | What does the product do, and for whom? | Product behavior (epics 1 to 6) | Current |
| 2 | [building-phase.md](./building-phase.md) | What ships in which phase? | Phase scope in one paragraph each | Current |
| 3 | [decisions.md](./decisions.md) | Which choices did we make, and why? | Provider choices, policy decisions, workarounds | Current (open items at the bottom) |
| 4 | [plan.md](./plan.md) | What exactly do we build and test, step by step? | Tasks, tests, exit gates, milestones, risks | Living checklist |
| 5 | [database.md](./database.md) | What does the data model look like? | Tables, constraints, Redis keys, purge rules | Design only |
| 6 | [api.md](./api.md) | What endpoints exist? | Endpoint contracts | Stub, fill as endpoints land |
| 7 | [external-tool-need.md](./external-tool-need.md) | Which accounts and keys do we need, and when? | Accounts, costs, dev workarounds | Current |

## Shortcuts by role

- **New to the project:** 1, then 2, then the "Decisions at a glance" table in plan.md section 1.
- **Building a phase:** the matching phase section in plan.md, then the tables it links to in database.md.
- **Setting up accounts:** external-tool-need.md only.
- **Why did we pick X?** decisions.md.

## Rules to keep the docs consistent

1. **Decisions change in decisions.md first.** Then update user-stories.md, building-phase.md and plan.md in the same change.
2. **Do not copy details between docs.** Link to the owner (schema to database.md, accounts to external-tool-need.md, endpoints to api.md).
3. **Tick checkboxes only in plan.md** (work) and external-tool-need.md (accounts). decisions.md has no checkboxes. Open questions go in its "Open items" section.
4. **Use the same names everywhere:** error codes such as `ALREADY_BOUND` and `ID_ALREADY_REGISTERED`, statuses such as `deactivating`, and `ended_reason` values. Their definitions live in database.md and plan.md.

## Known open mismatches

Listed here until resolved, so nobody trips over them.

- None. The last batch was resolved on 2026-11-17 and recorded in [decisions.md](./decisions.md) ("Resolved questions" 5 to 11).
