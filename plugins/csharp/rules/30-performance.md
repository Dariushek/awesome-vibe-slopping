## C# performance

- Readability first. Take the cheaper construct when it costs no readability. Never restructure code for speed without a measurement.
- `Span<T>` and `ReadOnlySpan<T>` over substrings and array copies for slicing and parsing.
- `readonly struct` or `ref struct` for small, short-lived values that would otherwise allocate.
- `ValueTask` when a method usually completes synchronously, `Task` otherwise. Never await a `ValueTask` twice or store it.
- No `async` state machine for a method that only returns another task, unless it has a `using` or `try` around the call.
