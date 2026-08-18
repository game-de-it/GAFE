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

## Publish v0.1.0

```sh
git tag -a v0.1.0 -m "GAFE v0.1.0"
git push origin v0.1.0

gh release create v0.1.0 \
  dist/GAFE-v0.1.0.zip \
  dist/SHA256SUMS \
  --repo game-de-it/GAFE \
  --title "GAFE v0.1.0" \
  --notes-file docs/releases/v0.1.0.md
```

Do not publish the tag or release until the final physical-device acceptance test has passed.
