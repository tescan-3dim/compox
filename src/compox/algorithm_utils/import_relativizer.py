"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import os
import ast


def _ensure_pkg_layout(root: str) -> None:
    """
    Ensure that all directories under root have __init__.py files.

    Parameters
    ----------
    root : str
        The root directory of the package.
    """
    for dp, _, _ in os.walk(root):
        init = os.path.join(dp, "__init__.py")
        if not os.path.exists(init):
            open(init, "w", encoding="utf-8").close()


def _collect_local_tops(pkg_root: str) -> set[str]:
    """
    Collect the top-level packages in a given package root.

    Parameters
    ----------
    pkg_root : str
        The root directory of the package.

    Returns
    -------
    set[str]
        A set of top-level package names.
    """
    tops = set()
    for name in os.listdir(pkg_root):
        p = os.path.join(pkg_root, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "__init__.py")):
            tops.add(name)
        elif name.endswith(".py"):
            tops.add(name[:-3])
    tops.discard("__init__")
    return tops


def _file_package_for(dirpath: str, pkg_root: str) -> str:
    """
    Compute the package name for a given directory path within the package root.
    Parameters
    ----------
    dirpath : str
        The directory path of the file.
    pkg_root : str
        The root directory of the package.
    Returns
    -------
    str
        The package name corresponding to the directory path.
    """
    rel = os.path.relpath(dirpath, pkg_root).replace(os.sep, ".").strip(".")
    return rel  # e.g. "", "utils", "models.seg"


def _split(dotted: str) -> list[str]:
    """
    Split a dotted module path into its components.
    Parameters
    ----------
    dotted : str
        The dotted module path.
    Returns
    -------
    list[str]
        A list of components in the dotted module path.
    """
    return [p for p in dotted.split(".") if p] if dotted else []


def _rel_level_and_module(from_pkg: str, to_abs: str) -> tuple[int, str | None]:
    """
    Compute (level, module) so that `from <module> import ...` with `level` dots
    imports the absolute target `to_abs` when used inside package `from_pkg`.

    Examples:
      from_pkg='models.seg', to_abs='utils.net'  -> (2, 'utils.net')  # from ..utils.net import ...
      from_pkg='models',     to_abs='models.seg' -> (1, 'seg')        # from .seg import ...
      from_pkg='',           to_abs='utils.net'  -> (1, 'utils.net')  # from .utils.net import ...
      from_pkg='utils',      to_abs='utils'      -> (1, None)         # from . import utils

    Parameters
    ----------
    from_pkg : str
        The package where the import is made.
    to_abs : str
        The absolute target module to import.
    Returns
    -------
    tuple[int, str | None]
        A tuple containing the level and module for the relative import.
    """
    fp = _split(from_pkg)
    tp = _split(to_abs)
    i = 0
    while i < min(len(fp), len(tp)) and fp[i] == tp[i]:
        i += 1
    up = len(fp) - i
    tail = ".".join(tp[i:])  # may be ""
    # 'from <module> import ...' with relative dots: level = up + 1
    # module is None if we import directly from the package we land in.
    return (up + 1, (tail or None))


class _Relativizer(ast.NodeTransformer):
    """
    Transform absolute imports to relative ones within a package.

    Parameters
    ----------
    local_tops : set[str]
        The top-level packages in the local directory.
    file_pkg : str
        The package name of the current file.
    """

    def __init__(self, local_tops: set[str], file_pkg: str):
        self.local = local_tops
        self.file_pkg = file_pkg

    def _is_local_abs(self, dotted: str) -> bool:
        """
        Check if a dotted module path is a local absolute import.

        Parameters
        ----------
        dotted : str
            The dotted module path.
        Returns
        -------
        bool
            True if the module is a local absolute import, False otherwise.
        """

        return bool(dotted) and dotted.split(".", 1)[0] in self.local

    def visit_Import(self, node: ast.Import):
        """
        Rewrite absolute intra-package imports to relative ones.

        - import X              -> if X is local: from <rel to X> import X as X
        - import X.Y           -> if X is local: also ensure submodule exists so X.Y is usable:
                                   emits:
                                     from <rel to X> import X as X
                                     from <same rel to X> import Y as _X_sub_unused
        External imports are left unchanged.

        Parameters
        ----------
        node : ast.Import
            The import node to process.
        Returns
        -------
        ast.AST
            The transformed AST node.
        """
        new_nodes: list[ast.stmt] = []
        for a in node.names:
            name = a.name
            top = name.split(".", 1)[0]
            if top in self.local:
                # 1) bind 'top' under the same name (or alias)
                level_top, mod_top = _rel_level_and_module(self.file_pkg, top)
                asname = a.asname or top
                new_nodes.append(
                    ast.ImportFrom(
                        module=mod_top,
                        names=[ast.alias(name=top, asname=asname)],
                        level=level_top,
                    )
                )
                # 2) if dotted, make sure first submodule is imported so X.Y attr exists
                if "." in name:
                    first_sub = name.split(".", 1)[1].split(".", 1)[0]
                    # from <rel to X> import <first_sub> as _X_sub_unused
                    new_nodes.append(
                        ast.ImportFrom(
                            module=mod_top if mod_top is not None else None,
                            names=[
                                ast.alias(
                                    name=first_sub, asname=f"_{top}_sub_unused"
                                )
                            ],
                            level=level_top,
                        )
                    )
            else:
                # external or non-local
                new_nodes.append(
                    ast.Import(names=[ast.alias(name=name, asname=a.asname)])
                )
        return (
            new_nodes[0]
            if len(new_nodes) == 1
            else ast.Module(body=new_nodes, type_ignores=[])
        )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """
        Absolute intra-package: compute correct (level, module) and rewrite.
        Relative imports: keep as-is.
        External absolutes: unchanged.

        Parameters
        ----------
        node : ast.ImportFrom
            The import-from node to process.
        Returns
        -------
        ast.AST
            The transformed AST node.
        """
        if node.level == 0 and node.module and self._is_local_abs(node.module):
            level, mod_tail = _rel_level_and_module(self.file_pkg, node.module)
            return ast.ImportFrom(
                module=mod_tail, names=node.names, level=level
            )
        return node  # keep relative and external as-is


def relativize_intra_package_imports(pkg_root: str) -> None:
    """
    Rewrite absolute intra-package imports to relative ones in all .py files
    under pkg_root.

    Parameters
    ----------
    pkg_root : str
        The root directory of the package.
    """
    _ensure_pkg_layout(pkg_root)
    local_tops = _collect_local_tops(pkg_root)

    for dp, _, files in os.walk(pkg_root):
        file_pkg = _file_package_for(dp, pkg_root)
        tx = _Relativizer(local_tops, file_pkg)
        for fn in files:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dp, fn)
            with open(fp, "r", encoding="utf-8") as f:
                src = f.read()
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            new_tree = tx.visit(tree)
            ast.fix_missing_locations(new_tree)
            new_src = ast.unparse(new_tree)
            if new_src != src:
                tmp = fp + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new_src)
                os.replace(tmp, fp)
