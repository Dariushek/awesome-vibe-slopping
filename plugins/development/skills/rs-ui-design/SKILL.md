---
name: rs-ui-design
description: Design the screens of an approved specification as a clickable prototype before planning. Use when a spec changes what users see, or when the user asks for a UI design, mockup or prototype. Optional step between rs-spec and rs-plan.
---

# UI design

The prototype shows how the spec's workflows look, so flow mistakes surface before code. It is a design, never production code.

## Steps

1. **Context.** Read the spec, the project's AGENTS.md, its design system or UI rules and the screens closest to this feature. If the spec is not `Approved`, stop and say so.
2. **Screens.** List every screen and state the workflows need, each mapped to the scenarios it shows. Include empty, loading, error, no-access and confirmation states that the scenarios or failures imply. Show the list to the user and wait for approval.
3. **Build.** Write the prototype to `prototype/` next to `SPEC.md`.
   - Use the project's own prototype setup if it has one, such as Storybook or a prototype route. Otherwise write static HTML with the project's tokens, fonts and component markup copied in.
   - Screens link to each other the way the workflows move. A state switcher shows the other states of each screen.
   - Data comes from the scenarios' concrete values. Never real customer data.
   - Every screen names its scenario IDs in a corner label.
4. **Check.** Open every screen and state with the playwright skill at phone and desktop widths. Fix overflow, broken links and anything that contradicts the design system.
5. **Review.** Show the user the screenshots and how to open the prototype. Iterate until they accept it.
6. **Link.** Set the spec's `Prototype:` line to the prototype path. Record visual decisions that apply beyond this feature, such as a new shared component, with rs-architecture-decision.
7. Next step: rs-plan.

## Rules

- Reuse existing components and patterns. A new one needs a reason the user accepts.
- Design system tokens only. No hardcoded colors, sizes or spacing the project does not already use.
- If the design reveals a gap in the domain, such as a missing state or outcome, set the spec back to `Draft`, fix it with rs-spec and resume here.
- Never edit application code while designing.
