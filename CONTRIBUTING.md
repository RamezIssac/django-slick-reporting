# Contributing

## Mutation testing

Pull requests to `develop` or `master` that change `slick_reporting/**.py` run `.github/workflows/mutation.yml`.
It mutates only the lines the PR adds or changes (mutmut 2.5.1), runs `python runtests.py` against each mutant and
posts the mutants, killed and surviving counts, with each survivor's `file:line` and diff, to the job summary and a
PR comment. It reports only: survivors do not fail the PR.

Run the same check locally from the repository root:

```bash
pip install -r tests/requirements.txt "mutmut[patch]==2.5.1"
git diff -U0 origin/develop... -- 'slick_reporting/*.py' > /tmp/pr.patch
mutmut run --use-patch-file /tmp/pr.patch
python scripts/mutation_report.py /tmp/pr.patch
```

The paths and the test runner live in the `[mutmut]` section of `setup.cfg`. `mutmut show <id>` prints one mutant.

A survivor is either a missing test or an equivalent mutant (no test can tell it from the original). Mark an
equivalent mutant with a pragma comment on its line that says why:

```python
separator = ", "  # pragma: no mutate: display text, no behaviour reads it
```

The pragma skips every mutant on that line.

## Public API surface

Pull requests to `develop` run `.github/workflows/api-surface.yml`. It loads `slick_reporting` at the PR's base and
head with griffe and lists the public names added, removed or changed: modules, classes, functions, methods and
module or class attributes, with their kind and signature or value. Public follows griffe: no leading underscore, not
imported, listed in `__all__` when the module defines it. Test and migrations modules and instance attributes are left
out. It reports only: it fails on tool errors, never on what it lists.

```bash
pip install "griffe==2.4.1"  # Python 3.11+
python scripts/api_surface.py "$(git merge-base origin/develop HEAD)" HEAD
```

## PR comments

Both reports go to the job summary and to one PR comment each, replaced on every push. The report job uploads
`comment.md` as the `pr-comment` artifact, and `.github/workflows/pr-comment.yml` (a `workflow_run` job, which also
works for fork PRs) posts it. The comment starts with a hidden marker naming the workflow, which picks the comment to replace. `workflow_run` jobs run from
`develop`, so a change to `pr-comment.yml` takes effect once merged.
