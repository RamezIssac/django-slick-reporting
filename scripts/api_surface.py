#!/usr/bin/env python
"""Print a markdown report of the public names of slick_reporting added, removed or changed between two git refs.

Usage: python scripts/api_surface.py BASE_REF [HEAD_REF]
"""

import ast
import os
import subprocess
import sys
import tempfile

import griffe

PACKAGE = "slick_reporting"
SKIPPED_MODULES = ("tests", "migrations")
EXPRESSION_KINDS = {
    griffe.ExprCall: "call",
    griffe.ExprDict: "dict",
    griffe.ExprList: "list",
    griffe.ExprSet: "set",
    griffe.ExprTuple: "tuple",
}


def describe(obj):
    if obj.is_function:
        return "method" if obj.parent.is_class else "function", obj.signature()
    if obj.is_class:
        return "class", f"({', '.join(str(base) for base in obj.bases)})"
    if obj.is_attribute:
        return f"{value_kind(obj.value)} attribute", str(obj.value)
    return obj.kind.value, ""


def value_kind(value):
    try:
        return type(ast.literal_eval(str(value))).__name__
    except (ValueError, SyntaxError):
        return EXPRESSION_KINDS.get(type(value), "expression")


def public_surface(obj):
    surface = {}
    for member in obj.members.values():
        if not member.is_public:
            continue
        if member.is_alias:
            surface[member.path] = ("alias", member.target_path)
            continue
        if "instance-attribute" in member.labels or (member.is_module and member.name in SKIPPED_MODULES):
            continue
        surface[member.path] = describe(member)
        if member.is_module or member.is_class:
            surface.update(public_surface(member))
    return surface


def load_surface(ref):
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(["git", "archive", ref, PACKAGE], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
        package = griffe.load(f"{tmp}/{PACKAGE}", allow_inspection=False)
        return public_surface(package)


def code(text, start=0, width=80):
    text = text if start == 0 else "..." + text[start:]
    text = text if len(text) <= width else text[: width - 3] + "..."
    return f"`{text}`" if text else ""


def change(before, after):
    start = max(0, len(os.path.commonprefix([before, after])) - 20)
    return f"{code(before, start, 60)} → {code(after, start, 60)}"


def table(title, rows):
    if not rows:
        return
    print(f"\n### {title}\n\n| Name | Kind | Signature or value |\n|---|---|---|")
    for path, kind, signature in rows:
        signature = signature.replace("|", r"\|")
        print(f"| `{path}` | {kind} | {signature} |")


def main(base_ref, head_ref="HEAD"):
    base, head = load_surface(base_ref), load_surface(head_ref)
    added = [(path, head[path][0], code(head[path][1])) for path in sorted(head.keys() - base.keys())]
    removed = [(path, base[path][0], code(base[path][1])) for path in sorted(base.keys() - head.keys())]
    changed = [
        (path, head[path][0], change(base[path][1], head[path][1]))
        for path in sorted(base.keys() & head.keys())
        if base[path] != head[path]
    ]

    if not (added or removed or changed):
        print("No public API changes.")
        return
    print(f"## Public API changes in `{PACKAGE}`\n")
    print(f"{len(added)} added, {len(removed)} removed, {len(changed)} changed.")
    table("Added", added)
    table("Removed", removed)
    table("Changed", changed)


if __name__ == "__main__":
    main(*sys.argv[1:])
