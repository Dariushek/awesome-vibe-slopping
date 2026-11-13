## C# collections

- Parameters take the most general type the method needs: `IEnumerable<T>` when it enumerates once, `IReadOnlyCollection<T>` or `IReadOnlyList<T>` when it needs the count, the index or a second pass.
- Public methods return `IReadOnlyList<T>`, or `IReadOnlyCollection<T>`, `IReadOnlySet<T>` or `IReadOnlyDictionary<K,V>` when that is the shape. Never a mutable collection.
- Return `IEnumerable<T>` or `IAsyncEnumerable<T>` only when the result is lazy on purpose, such as a stream too large to hold.
- `IQueryable<T>` and `Expression` never cross a repository's public API.
- A collection held by a domain object is immutable, not only read-only: `ImmutableArray<T>` or a private copy.
- Private and hot code keeps concrete types, such as `List<T>`, arrays and spans.
- Pick the collection by how it is read: `Dictionary` or `HashSet` for lookups by key, never a scan of a `List<T>`. `Queue<T>` for first-in first-out, never `Insert(0, ...)`.
- Set the capacity when the size is known or can be reasonably estimated.
- One lookup, not two: `TryGetValue` over `ContainsKey` followed by the indexer.
