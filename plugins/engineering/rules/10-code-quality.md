## Code quality

- Follow the project's architecture, with its layer and module boundaries. Never bypass a boundary it defines.
- Avoid magic numbers and strings by extracting recurring or meaningful values into descriptive constants or enums. Keep self-explanatory, one-off values inline to avoid clutter. If a value comes from a spec, such as HTTP 200 OK, use a constant regardless.
- Reduce code indentation. Avoid Arrow Anti-Pattern. Leverage early return and continue.
- Keep function names short, under 30 characters. Does not apply to test method names.
- Use enums instead of booleans for function parameters.
- Let the reader of the code breathe. Add empty lines between logical blocks of code.
- Expose as little as possible. Keep members private and modules' internals unexported unless the design requires access. Widening exposure is a design change and needs the user's approval, unless an approved spec, plan or the project's architecture names that surface.
- Program to levels of abstraction. Lower-level mechanics such as file access, HTTP clients or SQL must be encapsulated in a dedicated abstraction layer. Expose clean, high-level APIs so calling code works with domain concepts, not raw implementation details.
- Don't touch code unrelated to the feature you implement. Don't add comments to a block of code you did not create or modify. Minimize the number of changed lines.
