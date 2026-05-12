# Publishing to PyPI

This project publishes with GitHub Actions and PyPI Trusted Publishing. No PyPI
API token is required.

## One-time PyPI setup

1. Create or sign in to a PyPI account at `pypi.org`.
2. Decide whether the PyPI project already exists.
3. If `codex-tool-mock` does not exist on PyPI yet, create a pending publisher
   from your PyPI account's `Publishing` page. Set:
   - PyPI project name: `codex-tool-mock`
   - Owner: the GitHub organization or username that owns this repository.
   - Repository name: this repository name.
   - Workflow filename: `publish-pypi.yml`.
   - Environment name: `pypi`.
4. If `codex-tool-mock` already exists on PyPI, open that project's settings
   and add a trusted publisher with:
   - Owner: the GitHub organization or username that owns this repository.
   - Repository name: this repository name.
   - Workflow filename: `publish-pypi.yml`.
   - Environment name: `pypi`.
5. In this GitHub repository, create an environment named `pypi` under
   `Settings -> Environments`. Add required reviewers if you want a manual
   approval gate before publishing.

The workflow requests GitHub's OpenID Connect token with `id-token: write`, and
PyPI exchanges that token for publish permission when the repository, workflow,
and environment match the trusted publisher configuration.

## Release process

1. Update `version` in `pyproject.toml`.
2. Run local checks:

   ```bash
   uv run ruff format .
   uv run ruff check --fix --unsafe-fixes
   uv run pytest
   uv build
   ```

3. Commit the version change.
4. Create and push a version tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

5. GitHub Actions runs `.github/workflows/publish-pypi.yml`, builds the wheel
   and source distribution, then publishes them to PyPI.

You can also start the workflow manually from the GitHub Actions tab with
`workflow_dispatch`. Use manual runs carefully because PyPI does not allow
re-uploading the same version. The workflow uses `skip-existing: true`, so a
push to `main` with an already-published version is treated as a no-op publish.

## Trusted publisher troubleshooting

If publishing fails with:

```text
400 Non-user identities cannot create new projects
```

then PyPI accepted the GitHub Actions identity, but that identity is not allowed
to create the project being uploaded. Check the trusted publisher setup:

- The pending publisher's PyPI project name must be exactly `codex-tool-mock`,
  matching `name = "codex-tool-mock"` in `pyproject.toml`.
- The workflow filename must be exactly `publish-pypi.yml`.
- The GitHub environment must be exactly `pypi`, matching the workflow's
  `environment.name`.
- The GitHub owner and repository name must match the actual repository running
  the workflow.

If any pending publisher value is wrong, delete it and create a new pending
publisher with the corrected values.
