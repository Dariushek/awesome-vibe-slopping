## C# HTTP clients

- Never `new HttpClient()` per call. Get clients from `IHttpClientFactory`.
- Prefer typed clients: `AddHttpClient<TClient>()`, base address and headers set at registration.
- Never inject a typed client into a singleton. Use `IHttpClientFactory` there, or a static `SocketsHttpHandler` with `PooledConnectionLifetime`.
- Add resilience with `AddStandardResilienceHandler()` from `Microsoft.Extensions.Http.Resilience`. No hand-written retry loops.
- Retry only idempotent requests unless the endpoint supports idempotency keys.
- Pass `CancellationToken` to every send. Set timeouts in the resilience pipeline, not with `HttpClient.Timeout`.
- Dispose `HttpResponseMessage`. Read bodies with `ReadFromJsonAsync`, never `ReadAsStringAsync` then deserialize.
