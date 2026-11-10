## C#

- Follow the project's .editorconfig and analyzers.
- Never suppress an analyzer warning without a justification comment.
- Nullable reference types stay enabled. Use `!` only when non-null is proven, never to silence a warning.
- Async all the way. No `.Result` or `.Wait()`. Pass `CancellationToken` through.
- Prefer records for immutable data and DTOs.
- No interface for a single implementation, unless it crosses a module or layer boundary.
- When adding or removing an endpoint, update the project's `.http` file, if it has one.
