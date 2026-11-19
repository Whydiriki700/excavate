# excavate

Every git history is an archaeological site. excavate digs through yours and reports what the commits confess: which files are cursed, which are hot, which always change together, and who really owns each part of the tree. Zero dependencies beyond git itself.

## What it reports

- **Cursed files**: files touched by revert commits, ranked by how often history had to be undone around them.
- **Hotspots**: the most frequently changed files in the repository, the places where complexity and bugs tend to gather.
- **Always together**: file pairs that change in the same commit again and again, a sign of hidden coupling nobody documented.
- **Ownership map**: for each top level folder, the author behind most of its commits and their share.

## Usage

```bash
python -m excavate                    # dig the current repository
python -m excavate --root ../repo     # dig another repository
python -m excavate --top 5            # fewer rows per section
python -m excavate --since 2024-01-01 # only recent history
python -m excavate --json             # machine readable report
```

## Example output

```text
Commits: 412   Authors: 3   Files ever changed: 96

CURSED FILES (touched by revert commits)
     4 reverts   src/payments.py
     2 reverts   src/auth.py

HOTSPOTS (most changed files)
    57 changes   src/payments.py
    41 changes   README.md

ALWAYS TOGETHER (file pairs changed in the same commit)
    19 times   src/auth.py  +  tests/test_auth.py

OWNERSHIP MAP (dominant author per top level folder)
  src                      Alice  (78% of 210 commits)
```

## Requirements

Python 3.8 or newer, and git on PATH. No packages to install.

## License

MIT. See `LICENSE`.
