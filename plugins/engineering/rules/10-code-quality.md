## Code quality

- Follow the existing architecture in the project. Look for ADRs, if there aren't any, derive them based on the existing code.
- Avoid magic numbers and strings by extracting recurring or meaningful values into descriptive constants or enums. Keep self-explanatory, one-off values inline to avoid clutter. If a value comes from a spec, such as HTTP 200 OK, use a constant regardless.
- Reduce code indentation. Avoid Arrow Anti-Pattern. Leverage early return and continue.
- Keep function names short, under 30 characters. Does not apply to test method names.
- Use enums instead of booleans for function parameters.
- No interface until at least two implementations exist.
- Let the reader of the code breathe. Add empty lines between logical blocks of code.
- Treat member visibility changes as a breaking design shift. Keep all fields and functions private unless external access is strictly required by the design. Ask the user for explicit approval before changing any access modifier from private to internal or public.
- Program to levels of abstraction. Lower-level mechanics such as raw hardware I/O, sector parsing or direct socket streams must be encapsulated in a dedicated driver or abstraction layer. Expose clean, high-level APIs so calling code works with domain concepts, not raw implementation details.
- Strictly adhere to the layered boundary hierarchy: each layer may only communicate with its immediate neighbor directly below it. Never punch holes through layers. Controllers or UI components must never directly call database queries, raw hardware drivers or low-level network clients; always route through the intermediate service or abstraction layer.
- Don't touch code unrelated to the feature you implement. Don't add comments to a block of code you did not create or modify. Minimize the number of changed lines.
- When adding or removing an endpoint, update the .http test file.
