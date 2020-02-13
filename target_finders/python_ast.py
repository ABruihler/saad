import ast
import asttokens

def iter_fields(node):
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass

def node_to_string(node):
    out = type(node).__name__

    if isinstance(node, ast.ClassDef):
        out += ': ' + node.name
    elif isinstance(node, ast.FunctionDef):
        out += ': ' + node.name

    if hasattr(node, 'first_token') and hasattr(node, 'last_token'):
        start = ':'.join(map(str, node.first_token.start))
        end = ':'.join(map(str, node.last_token.end))
        out += '(' + start + ' - ' + end + ')'

    return out

class Visitor(ast.NodeVisitor):
    def generic_visit(self, node, deep=0):
        """Called if no explicit visitor function exists for a node."""
        prefix = '-' * deep
        print(prefix + node_to_string(node))

        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.generic_visit(item, deep + 1)
            elif isinstance(value, ast.AST):
                self.generic_visit(value, deep + 1)

with open(__file__, 'rb') as src_stream:
    source = src_stream.read()
    atok = asttokens.ASTTokens(source, parse=True)
    visitor = Visitor()
    visitor.visit(atok.tree)
