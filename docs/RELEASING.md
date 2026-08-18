# Release Procedure

## Prepare

```sh
./scripts/release-check.sh
```

The command verifies source syntax, required files, a clean Git worktree, ZIP integrity, and SHA-256 output.

## Create and Push the Repository

The expected public repository is `game-de-it/GAFE`.

```sh
gh repo create game-de-it/GAFE --public --source=. --remote=origin --push
```

If the repository already exists:

```sh
git remote add origin https://github.com/game-de-it/GAFE.git
git push -u origin main
```

## Publish the current version

```sh
version=$(tr -d '\r\n' < ports/GAFE/VERSION)
git tag -a "v$version" -m "GAFE v$version"
git push origin "v$version"

gh release create "v$version" \
  "dist/GAFE-v$version.zip" \
  "dist/SHA256SUMS" \
  --repo game-de-it/GAFE \
  --title "GAFE v$version" \
  --notes-file "docs/releases/v$version.md"
```

Do not publish the tag or release until the final physical-device acceptance test has passed.
