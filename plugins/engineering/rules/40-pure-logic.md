## Pure logic

- Everything that holds logic is pure: the same input gives the same output, with no side effects.
- Impure work stays outside, in a thin shell, such as database access, network calls, files and logging. The shell gathers the input, calls the pure code and acts on what it returns.
- The shell decides nothing. A business rule in it belongs in the pure code.
- Pure code takes the current time, random values and new ids as arguments, never from the environment.
- Pure code never logs. It returns what happened as data and the shell logs it, such as with a visitor over the result.
