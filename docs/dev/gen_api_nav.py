"""Generate API documentation stubs and a literate-nav summary for the Developer Guide.

This script is executed by MkDocs via the `mkdocs-gen-files` plugin to produce:
  1) **Package index pages** under `docs/dev/api/…/*.md` for every package
     (`__init__.py`) within `src/calista`. These pages always exist and act as
     indexes listing immediate **Subpackages** and **Modules** with links.
     If a package’s `__init__.py` contains a module-level docstring, the page
     also includes a mkdocstrings directive (`::: package.module`) so the
     package-level docs render above the index.
  2) **Concrete module pages** under `docs/dev/api/…/*.md` for every non-package
     Python module. Each page contains a mkdocstrings directive to render the
     module API from docstrings.
  3) A **literate navigation file** at `docs/dev/api/SUMMARY.md` whose links are
     *relative to `docs/dev/api/`*. This file is consumed by the
     `mkdocs-literate-nav` plugin to populate the “API” section of the site.

Integration (in `mkdocs.yml` for a single-site, User/Developer split):
    plugins:
      - gen-files:
          scripts:
            - docs/dev/gen_api_nav.py
      - literate-nav:
          nav_file: dev/api/SUMMARY.md     # path relative to docs/
      - mkdocstrings:
          handlers:
            python:
              paths: [src]                  # required for a src/ layout
              options:
                docstring_style: google
                members_order: source
                show_source: false

Notes & gotchas:
- Links inside `SUMMARY.md` must be **relative to `dev/api/`**. Do not prefix
  them with `dev/api/`, or MkDocs will resolve them as `dev/api/dev/api/...`.
- Private names (starting with “_”) and packages/modules without code docs are
  skipped for mkdocstrings rendering, but packages always get an index page.
- This script *parses* files with `ast` to detect module docstrings; it does not
  import packages, avoiding import-time side effects during the docs build.
"""

from pathlib import Path
import ast
import mkdocs_gen_files
from mkdocs_gen_files.nav import Nav

PKG_ROOT = Path("src") / "calista"      # your package root
API_DIR = Path("dev") / "api"           # docs/dev/api/
NAV_FILE = API_DIR / "SUMMARY.md"       # docs/dev/api/SUMMARY.md

nav = Nav()

def has_module_docstring(py_path: Path) -> bool:
    """Return True if the file has a non-empty module-level docstring.

    The file is parsed with `ast` to avoid importing it (no side effects).
    """
    try:
        text = py_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    try:
        node = ast.parse(text)
    except SyntaxError:
        return False

    return bool(ast.get_docstring(node))

def write_md(path: Path, content: str) -> None:
    """Write Markdown `content` to `path` using mkdocs-gen-files’ virtual FS."""
    with mkdocs_gen_files.open(path, "w") as file_writer:
        file_writer.write(content)

# 1) Package index pages (ALWAYS create; include ::: only if docstring exists)
for init in sorted(PKG_ROOT.rglob("__init__.py")):
    # ["calista","adapters","filestore","__init__"] -> drop "__init__"
    rel = init.relative_to("src").with_suffix("")
    parts = list(rel.parts[:-1])
    if not parts or any(p.startswith("_") for p in parts):
        continue

    PKG_MODULE = ".".join(parts)                               # e.g. calista.adapters.filestore
    pkg_dir_fs = PKG_ROOT.joinpath(*parts[1:])              # e.g. src/calista/adapters/filestore
    doc_path = API_DIR / Path(*parts).with_suffix(".md")    # docs/dev/api/.../filestore.md

    # Discover immediate children
    child_modules = sorted(
        m.stem for m in pkg_dir_fs.glob("*.py")
        if m.name != "__init__.py" and not m.stem.startswith("_")
    )
    child_packages = sorted(
        d.name for d in pkg_dir_fs.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "__init__.py").exists()
    )

    leaf = parts[-1]
    lines: list[str] = [f"# `{PKG_MODULE}`\n"]

    # Only include mkdocstrings block if the package has a docstring
    if has_module_docstring(init):
        lines += [
            f"::: {PKG_MODULE}\n",
            "    options:\n",
            "      show_root_heading: true\n",
            "      members_order: source\n",
            "      docstring_style: google\n",
            "      show_source: false\n",
            "      filters:\n",
            "        - '!^_'\n",
        ]

    if child_packages:
        lines.append("\n## Subpackages\n")
        for name in child_packages:
            lines.append(f"- [{name}]({leaf}/{name}.md)\n")

    if child_modules:
        lines.append("\n## Modules\n")
        for name in child_modules:
            lines.append(f"- [{name}]({leaf}/{name}.md)\n")

    write_md(doc_path, "".join(lines))
    # Nav link RELATIVE to dev/api/
    nav[tuple(parts)] = Path(*parts).with_suffix(".md").as_posix()

# 2) Concrete module pages
for py in sorted(PKG_ROOT.rglob("*.py")):
    if py.name == "__init__.py":
        continue
    rel = py.relative_to("src").with_suffix("")
    parts = list(rel.parts)
    if not parts or any(p.startswith("_") for p in parts):
        continue

    MODULE = ".".join(parts)
    doc_path = API_DIR / Path(*parts).with_suffix(".md")

    write_md(
        doc_path,
        "\n".join([
            f"# `{MODULE}`",
            "",
            f"::: {MODULE}",
            "    options:",
            "      show_root_heading: true",
            "      members_order: source",
            "      docstring_style: google",
            "      show_source: false",
            "      filters:",
            "        - '!^_'",
            ""
        ])
    )
    nav[tuple(parts)] = Path(*parts).with_suffix(".md").as_posix()

# 3) Emit literate-nav (links are RELATIVE to dev/api/)
with mkdocs_gen_files.open(NAV_FILE, "w") as f:
    f.writelines(nav.build_literate_nav())
