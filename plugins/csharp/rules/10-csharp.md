## C#

- Follow the project's .editorconfig and analyzers.
- Never suppress an analyzer warning without a justification comment.
- Nullable reference types stay enabled. Use `!` only when non-null is proven, never to silence a warning.
- Async all the way. No `.Result` or `.Wait()`. Pass `CancellationToken` through.
- Prefer records for immutable data and DTOs.
