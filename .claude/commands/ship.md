Run quality checks, commit staged changes, push, and open a PR targeting `develop`.

Steps:
1. Run `poetry run ruff check . --fix --unsafe-fixes && poetry run ruff format .` and fix any remaining issues.
2. Run `poetry run mypy` — fix all type errors before continuing.
3. Run `poetry run pytest tests` — fix any failures before continuing.
4. Show a `git diff --staged` summary and ask the user to confirm the commit message, or draft one following the repo convention (`feat:`, `fix:`, `chore:`, etc.).
5. Commit, push the current branch, and open a PR with `gh pr create --base develop`. Include "Closes #<N>" in the PR body if an issue number is known.
6. Return the PR URL.

Do not proceed past any failing step — fix the issue first.
