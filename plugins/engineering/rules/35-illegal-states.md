## Illegal states

- Make illegal states unrepresentable. A state the rules forbid must not compile.
- Model alternatives as a union and combinations as a record. Never one type with a flag and fields that are valid only for some values of it.
- Data that exists in one case only lives in that case, never as a nullable field on all of them.
- Match on every case with no default branch, so a new case breaks the build wherever it is not handled.
- What the type system cannot express, such as a positive-only number, the smart constructor checks.
