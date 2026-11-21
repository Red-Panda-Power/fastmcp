"""Compatibility shims for CLI dependencies on older Python versions."""

# ruff: noqa: S307, UP006, UP035, UP036

from __future__ import annotations

import ast
import inspect
import sys
from collections.abc import Callable
from typing import Any, ClassVar, Dict, List, Set, Tuple, Type, Union


class _Python38AnnotationTransformer(ast.NodeTransformer):
    """Translate postponed PEP 585 and PEP 604 annotations for Python 3.8."""

    _builtin_generics: ClassVar[dict[str, str]] = {
        "dict": "_Dict",
        "list": "_List",
        "set": "_Set",
        "tuple": "_Tuple",
        "type": "_Type",
    }

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        visited = self.generic_visit(node)
        assert isinstance(visited, ast.BinOp)
        node = visited
        if isinstance(node.op, ast.BitOr):
            slice_value: ast.AST = ast.Tuple(
                elts=[node.left, node.right], ctx=ast.Load()
            )
            if sys.version_info < (3, 9):
                slice_value = ast.Index(value=slice_value)
            return ast.copy_location(
                ast.Subscript(
                    value=ast.Name(id="_Union", ctx=ast.Load()),
                    slice=slice_value,
                    ctx=ast.Load(),
                ),
                node,
            )
        return node

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        visited = self.generic_visit(node)
        assert isinstance(visited, ast.Subscript)
        node = visited
        if isinstance(node.value, ast.Name) and node.value.id in self._builtin_generics:
            node.value = ast.copy_location(
                ast.Name(id=self._builtin_generics[node.value.id], ctx=ast.Load()),
                node.value,
            )
        return node


def _resolve_annotation(annotation: Any, globalns: dict[str, Any]) -> Any:
    if not isinstance(annotation, str):
        return annotation

    tree = ast.parse(annotation, mode="eval")
    tree = _Python38AnnotationTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    namespace = dict(globalns)
    namespace.update(
        {
            "_Dict": Dict,
            "_List": List,
            "_Set": Set,
            "_Tuple": Tuple,
            "_Type": Type,
            "_Union": Union,
        }
    )
    return eval(compile(tree, "<annotation>", "eval"), namespace)


def install_cyclopts_py38_annotation_support() -> None:
    """Teach Cyclopts 2.x to resolve postponed modern annotations on Python 3.8."""
    if sys.version_info >= (3, 9):
        return

    import cyclopts.utils

    if getattr(cyclopts.utils, "_fastmcp_py38_signature", None) is not None:
        return

    original_signature: Callable[..., inspect.Signature] = cyclopts.utils.signature

    def signature(function: Any) -> inspect.Signature:
        resolved = original_signature(function)
        if not getattr(function, "__module__", "").startswith("fastmcp.cli"):
            return resolved
        globalns = getattr(function, "__globals__", None)
        if globalns is None:
            return resolved

        parameters = [
            parameter.replace(
                annotation=_resolve_annotation(parameter.annotation, globalns)
            )
            for parameter in resolved.parameters.values()
        ]
        return resolved.replace(
            parameters=parameters,
            return_annotation=_resolve_annotation(resolved.return_annotation, globalns),
        )

    cyclopts.utils.signature = signature
    cyclopts.utils._fastmcp_py38_signature = original_signature
