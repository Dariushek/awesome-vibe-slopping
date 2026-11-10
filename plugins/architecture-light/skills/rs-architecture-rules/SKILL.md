---
name: rs-architecture-rules
description: Write short architecture rules into the project's AGENTS.md, without ADRs or diagrams. Use in projects with the architecture-light bundle, when they have no architecture rules yet, or when the user asks to set or change them.
---

# Architecture rules

If the project has `.agents/overrides/rs-architecture-rules.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. **Context.** Read AGENTS.md and the code structure: projects or packages, folders, references between parts.
2. **Draft.** Write the rules the code already follows. Mark every guess `???`.
3. **Ask.** One round of at most five questions, numbered `Q1` and onward, on what the code does not answer: modules and what each owns, who may use whom, how parts communicate, layers, where code goes. Stop and wait for the answers. The user may answer that a topic does not apply.
4. **Write.** Put the rules in a `## Architecture` section of AGENTS.md, outside any generated block. Show them and iterate until the user approves.
5. **Check.** If a rule is cheap to test, such as a module not referencing another, offer an automated check in the validation gate.

## Template

```markdown
## Architecture

- Three modules: Orders, Billing, Catalog. Each owns its data.
- API endpoints call modules only through their facade.
- Writes go through commands with one handler each.
- Modules never reference each other's internals.
```

## Rules

- At most ten rules, each one line, concrete enough to say whether code breaks it.
- Only rules the project follows now or the user decided. No plans.
- Changing a rule needs the user's OK.
