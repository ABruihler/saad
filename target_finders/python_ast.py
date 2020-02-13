import ast
import asttokens
import re
from collections import namedtuple

token_sub_regex = r'[^\s\(\)]+'
token_regex = r'^' + token_sub_regex + r'$'
named_token_regex = r'^(' + token_sub_regex + r')\((' + token_sub_regex + r')\)$'

Token = namedtuple('Token', 'type direct_child')
NamedToken = namedtuple('NamedToken', 'type name direct_child')

def parse_ast_location(location_str):
    tokens = location_str.split()
    parsed = []
    direct_child = False

    for token in tokens:
        if token == '>':
            direct_child = True
        elif re.match(token_regex, token):
            parsed.append(Token(token, direct_child))
            direct_child = False
        elif re.match(named_token_regex, token):
            match = re.match(named_token_regex, token)
            parsed.append(NamedToken(match.group(1), match.group(2), direct_child))
            direct_child = False

    return parsed

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

class Visitor():
    # def old_visit(self, node, deep=0):
    #     """Called if no explicit visitor function exists for a node."""
    #     prefix = '-' * deep
    #     print(prefix + node_to_string(node))

    #     for field, value in iter_fields(node):
    #         if isinstance(value, list):
    #             for item in value:
    #                 if isinstance(item, ast.AST):
    #                     self.generic_visit(item, deep + 1)
    #         elif isinstance(value, ast.AST):
    #             self.generic_visit(value, deep + 1)

    def visit(self, node, location):
        target = location[0]

        if target.type == 'class':
            if isinstance(node, ast.ClassDef) and node.name == target.name:
                location = location[1:]
            elif target.direct_child:
                return
        elif target.type == 'func':
            if isinstance(node, ast.FunctionDef) and node.name == target.name:
                location = location[1:]
            elif target.direct_child:
                return

        if len(location) == 0:
            print(node)
            return

        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item, location)
            elif isinstance(value, ast.AST):
                self.visit(value, location)

with open(__file__, 'rb') as src_stream:
    source = src_stream.read()
    atok = asttokens.ASTTokens(source, parse=True)
    visitor = Visitor()
    location = parse_ast_location('class(Visitor) > func(visit)')
    visitor.visit(atok.tree, location)
