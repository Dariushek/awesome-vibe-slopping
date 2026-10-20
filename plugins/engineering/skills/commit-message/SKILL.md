---
name: commit-message
description: Write a git commit message following the house rules. Use whenever creating a commit or asked to write or fix a commit message.
---

# Commit message

1. Start the subject with the task number from the branch name, as `#12345`. If the branch name has none, ask.
2. Separate subject and body with one blank line.
3. Subject: 50 characters, 72 hard limit.
4. Capitalize the first letter of the subject.
5. No period at the end of the subject.
6. Imperative mood. It must complete: "If applied, this commit will ...".
7. Wrap the body at 72 characters.
8. Body explains what and why, not how. The code shows the how.

Get the branch with `git branch --show-current`.

Example:

```
#4821 Retry token refresh on clock skew

Refresh failed when the server clock ran ahead of the client by more
than the token leeway. Users were logged out mid-session.
```
