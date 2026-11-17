## .NET solution

- Files outside projects stay visible in the solution, in solution folders that mirror their directories, as Visual Studio solution items do. Root files go to `Solution Items`. This covers docs, pipeline definitions, README and build configuration such as `.editorconfig`, `global.json` and `Directory.Build.props`.
- After adding, moving or deleting such a file, run `.githooks/solution-items --fix` with Python. Never edit solution folders by hand.
- `.agents/solution-items.json` extends the defaults with `include` and `exclude` path patterns.
- The project's `.agents/validation.json` runs `{python} .githooks/solution-items` in `commit`. When it is missing, offer to add it.
