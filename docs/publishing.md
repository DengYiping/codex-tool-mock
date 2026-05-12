# Publishing to PyPI

This project publishes with GitHub Actions and PyPI Trusted Publishing. No PyPI
API token is required.

## One-time PyPI setup

1. Create or sign in to a PyPI account at `pypi.org`.
2. Create the `codex-tool-mocks` PyPI project once. The first upload can create
   it automatically if the package name is available, but creating it manually
   first makes the trusted publisher setup clearer.
3. In PyPI, open the project settings and add a trusted publisher:
   - Owner: the GitHub organization or username that owns this repository.
   - Repository name: this repository name.
   - Workflow filename: `publish-pypi.yml`.
   - Environment name: `pypi`.
4. In this GitHub repository, create an environment named `pypi` under
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
re-uploading the same version.
