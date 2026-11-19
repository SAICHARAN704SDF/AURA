"""Bounded scholarly search and a small numerical expression interpreter."""
import ast
import math
import operator

import httpx

from aura.core import ServiceError


async def search_publications(query):
    """Search Crossref's public metadata index. Only the search terms leave AURA."""
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await client.get("https://api.crossref.org/works", params={
                "query.bibliographic": query, "rows": 5, "select": "title,DOI,published"
            })
            response.raise_for_status()
            items = response.json()["message"]["items"]
            return {"publications": [{"title": (item.get("title") or [""])[0][:400],
                                      "doi": item.get("DOI"), "published": item.get("published")}
                                     for item in items[:5]], "source": "Crossref"}
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise ServiceError("publication_search_unavailable") from exc


def evaluate_program(program):
    """Interpret arithmetic assignments and a final expression using bounded floats only."""
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    names = {}
    def value(node):
        if isinstance(node, ast.Constant) and type(node.value) in (float, int):
            result = float(node.value)
        elif isinstance(node, ast.Name) and node.id in names:
            result = names[node.id]
        elif isinstance(node, ast.BinOp) and type(node.op) in ops:
            result = ops[type(node.op)](value(node.left), value(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            result = value(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        else:
            raise ValueError()
        if not math.isfinite(result):
            raise ValueError()
        return result

    try:
        if len(program)>1000:
            raise ValueError()
        tree = ast.parse(program, mode="exec")
        if len(list(ast.walk(tree))) > 100 or not tree.body or not isinstance(tree.body[-1], ast.Expr):
            raise ValueError()
        for statement in tree.body[:-1]:
            if not isinstance(statement, ast.Assign) or len(statement.targets)!=1 or not isinstance(statement.targets[0], ast.Name):
                raise ValueError()
            names[statement.targets[0].id] = value(statement.value)
        return {"result": value(tree.body[-1].value)}
    except (ValueError, SyntaxError, RecursionError, ArithmeticError) as exc:
        raise ServiceError("invalid_numeric_program") from exc
