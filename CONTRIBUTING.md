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
