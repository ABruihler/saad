import ast

with open(__file__, 'rb') as src_stream:
    print(ast.dump(ast.parse(src_stream.read())))