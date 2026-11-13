## Testing

- Write automated tests with TDD: first a failing test, then the implementation that makes it pass. Never both at the same time.
- The test must fail on its assertion about the behavior under test, such as a status left unset or at its default. A compile error, a runtime exception or a broken setup is no valid failure. Add just enough code to reach the assertion, such as an empty method.
- When fixing a bug, don't write the fix right away. Write the test, observe it failing, write the fix, observe the test passing.
- During the loop run only the tests the change affects. Before a commit run all automated tests, except those the project runs before a push, such as end-to-end tests.
- A new feature that changes no existing behavior leaves existing tests untouched. When one of them fails, fix the code, never the test.
- When changing existing behavior, change its tests first, observe them failing, then change the implementation.
- Name a test after one behavior of the system, in domain words, such as `Book_out_of_copies_cannot_be_rented`. Never after a method, a class or an implementation detail.
- One behavior per test.
- The test body highlights the behavior under test: the values that drive it, the action and the outcome. Everything else is noise; hide it behind helper methods with domain names.
