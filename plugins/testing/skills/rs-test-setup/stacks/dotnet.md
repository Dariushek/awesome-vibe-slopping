# .NET recipe

Use the test framework the project has. For a new test project use TUnit.

When `dotnet new list` shows the `RS integration tests` template, create the test project with it and skip to the first test: it brings the container setup and the fixture below. Add the project with `dotnet sln add <project> --include-references false`.

## Parts

| Part | Tool |
|------|------|
| App in-process | `WebApplicationFactory<Program>` from `Microsoft.AspNetCore.Mvc.Testing` |
| Database in a container | Testcontainers, such as `Testcontainers.MsSql` or `Testcontainers.PostgreSql` |
| In-memory provider | `Microsoft.EntityFrameworkCore.InMemory` |
| End-to-end | `Microsoft.Playwright` |

## Container, once per test run

```csharp
internal static class DatabaseSetup
{
    private static MsSqlContainer? container;
    private static string rootConnectionString = null!;

    [Before(Assembly)]
    public static async Task StartAsync()
    {
        container = new MsSqlBuilder(Image)
            .WithTmpfsMount("/var/opt/mssql/data")
            .WithTmpfsMount("/var/opt/mssql/log")
            .WithTmpfsMount("/var/opt/mssql/secrets")
            .Build();

        await container.StartAsync();
        rootConnectionString = container.GetConnectionString();
    }

    [After(Assembly)]
    public static async Task StopAsync()
    {
        if (container is { })
            await container.DisposeAsync();
    }

    public static string ConnectionStringFor(string databaseName)
    {
        return new SqlConnectionStringBuilder(rootConnectionString)
        {
            InitialCatalog = databaseName
        }.ConnectionString;
    }
}
```

- Pin the image tag. Mount the data directories of the engine on tmpfs.
- One container per run, one database per test.

## Long-lived container, optional

Offer it when starting the container takes more than a few seconds of every run. Two parts:

A script at the project root, `db-dev.sh`, with four commands:

| Command | Does |
|---------|------|
| `up` | Starts the container when it is not running. Removes a stopped one first and creates it again, never restarts it. |
| `down` | Removes the container. |
| `status` | Shows whether it runs and on which port. |
| `clean` | `down`, then `up`. The way to drop the test databases that pile up. |

- Same image tag and the same tmpfs mounts as the container the tests start.
- A container name unique to the project and a fixed host port that is no default of the engine, such as 14330 for SQL Server.
- A password that is used nowhere else. It is committed, so it protects nothing.
- An unknown command prints the usage and exits with 1.

A check in the test setup, before the container starts:

```csharp
if (await IsReachableAsync(longLivedConnectionString))
{
    rootConnectionString = longLivedConnectionString;
    return;
}
```

- Try to open a connection with a timeout of one second. Any failure means not reachable.
- When reachable, start no container. Otherwise start one as above, which is what CI gets.
- Host, port and password in the setup match the script. Say so in a comment on both sides.
- Create each test database over a connection, never through the shell of the container. The tests did not start this one.
- The tests pass the same way with and without it. Nothing may require the script.

## Fixture, once per test

```csharp
internal abstract class ApiFixture
{
    private WebApplicationFactory<Program> factory = null!;
    protected HttpClient Client { get; private set; } = null!;
    protected FakeMailSender Mail { get; } = new();

    [Before(Test)]
    public void SetUp()
    {
        var connectionString = DatabaseSetup.ConnectionStringFor($"test_{Guid.NewGuid():N}");

        factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.ConfigureServices(services =>
            {
                services.RemoveAll<DbContextOptions<AppDbContext>>();
                services.AddDbContext<AppDbContext>(options => options.UseSqlServer(connectionString));
                services.RemoveAll<IMailSender>();
                services.AddSingleton<IMailSender>(Mail);
            }));

        using var scope = factory.Services.CreateScope();
        scope.ServiceProvider.GetRequiredService<AppDbContext>().Database.EnsureCreated();
        Client = factory.CreateClient();
    }

    [After(Test)]
    public void TearDown()
    {
        Client.Dispose();
        factory.Dispose();
    }

    protected async Task<Guid> GivenRegisteredBookAsync(RegisterBook command)
    {
        var response = await Client.PostAsJsonAsync("/books", command);
        var result = await response.Content.ReadFromJsonAsync<BookRegistration>();

        return result!.BookId;
    }
}
```

- When the project uses migrations, apply them instead of `EnsureCreated`, so the tests cover them.
- Never drop the database after a test. The container goes away with the run; dropping is slow and flaky.
- When there is no web host, build the same fixture on a `ServiceCollection` with the module's registration and call its public API.

## Test

```csharp
internal class BookRentingTests : ApiFixture
{
    [Test]
    public async Task Book_out_of_copies_cannot_be_rented()
    {
        var bookId = await GivenRegisteredBookAsync(new RegisterBook("978-0-13-468599-1", "Clean Code", copies: 1));
        await GivenRentedBookAsync(bookId);

        var response = await Client.PostAsync($"/books/{bookId}/rent", null);

        await Assert.That(response.StatusCode).IsEqualTo(HttpStatusCode.Conflict);
    }
}
```

## Without containers

- EF Core: `UseInMemoryDatabase(name, root)`. Pass one shared `InMemoryDatabaseRoot` to every call, or scopes stop seeing each other's rows.
- Compute the database name in a variable before the options lambda. The lambda runs more than once, so an inline `Guid.NewGuid()` gives a different database each time.
- The in-memory provider checks no constraints and runs no real SQL. Raw SQL, transactions and unique indexes need the container tier.
- No EF Core: a hand-written fake repository behind the repository interface.

## End-to-end

- The suite starts the app on a real port with a fresh database and the same fakes. On .NET 10 or later use `UseKestrel` and `StartServer` on `WebApplicationFactory`; before that, start the app as a process and wait for its health endpoint.
- A separate frontend is built once per run and served by the app or started next to it.
- Mark the tests with a category, such as `[Category("E2E")]`, so the commit stage can leave them out and the push stage can select them.
- Select elements by role or label, never by CSS class.
