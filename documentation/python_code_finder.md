# Python Code Finder

The Python code finder/Python AST module allows for locating specific blocks of code within a Python file. The code for this module is located in [scripts/target_finders/python_ast.py](../scripts/target_finders/python_ast.py).

The module is named `pythonAst` and takes two arguments:

1. `file`: The path of the file where the code is located.
2. `astLocation`: The location of the code within the file. The syntax for this is explained below.

## Specifying code location

The module has a simple syntax (similar to that of CSS) for specifying the location of the code which we are targeting. Currently, we support classes and functions.

Three pieces of syntax:

1. `class(ClassName)` targets a class named `ClassName`
2. `func(function_name)` targets a function named `function_name`
3. `>` specifies that we are only looking for direct descendants

Examples:

- `class(TestClass)` matches class(es) named TestClass
- `func(simple_function)` matches functions named simple_function
- `class(TestClass) func(simple_function)` only functions inside the class
- `class(TestClass) > func(simple_function)` only functions that are direct children of class (class methods)
- `> func(simple_function)` only global functions (direct children of root)

## Module output

The module outputs the path of the file where the code is located, the start line and column (both line and column are inclusive), and the end line and column (the line is inclusive, the column is exclusive). The output is on three separate lines. First comes the file path, then the start location, then the end location. The code locations are specified as `<line>:<column>`.

Example output:
```console
$ python3 scripts/target_finders/python_ast.py lots_of_code.py "class(CrazyClass) > func(critical_method)"
lots_of_code.py
6:5
7:31
```

## Attribution

The Python code finder was developed by Sebastian Kimberk.
