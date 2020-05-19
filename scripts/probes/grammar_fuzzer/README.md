## Python environment

First, create virtual environment for installing dependencies:

```
python3 -m venv env
```

Then, activate the virtual environment. You will do this whenever you start working on the project:

```
source env/bin/activate
```

To install dependencies:

```
python3 -m pip install -r requirements.txt
```


To leave the virtual environment:

```
deactivate
```

## Setting up ANTLR

Copied `ANTLRv4LexerPythonTarget.g4`, `ANTLRv4Parser.g4`, `LexBasic.g4`, and `LexerAdaptor.py` from the `antlr/grammars-v4` repo (located here: https://github.com/antlr/grammars-v4/tree/master/antlr/antlr4).

Renamed `ANTLRv4LexerPythonTarget.g4` to `ANTLRv4Lexer.g4` and also replaced occurences of former name with latter inside the file:

```
mv ANTLRv4LexerPythonTarget.g4 ANTLRv4Lexer.g4 && perl -pi -e s,ANTLRv4LexerPythonTarget,ANTLRv4Lexer,g ANTLRv4Lexer.g4
```

I removed the following part of `ANTLRv4Lexer.g4` as it was causing the error `ModuleNotFoundError: No module named 'LexerAdaptor'` and removing it fixed it (it gets imported anyway):

```
@header {
from LexerAdaptor import LexerAdaptor
}
```

Downloaded ANTLR using:

```
curl -O https://www.antlr.org/download/antlr-4.8-complete.jar
```

Ran using:

```
java -jar antlr-4.8-complete.jar ...
```

So, for the ANTLRv4 grammar:

```
java -jar antlr-4.8-complete.jar -Dlanguage=Python3 ANTLRv4Lexer.g4 ANTLRv4Parser.g4 LexBasic.g4 -o compiled && cp LexerAdaptor.py compiled/LexerAdaptor.py
```

## Calculating minimum depth

We are calculating the minimum depth required to generate from any node so that we can limit our choices when generating in order to avoid stack overflows. We're defining the depth of a node to be the minimum number of recursive steps required to generate output for that node.

For `Alternatives` node, we take the minimum depth of all its children (plus one).

For optional nodes (so quantifiers `*` and `?`) the minimum depth is zero.

For terminal (i.e. leaf) nodes the minimum depth is zero.

Otherwise, for a node that needs all its children, the depth is the maximum of the depths of all its children (plus one).

### Circular dependencies

I'm running into issues figuring out the depth for nodes with circular dependencies. Currently, I'm doing a depth first search and setting depth of the current node based on depths of children.

A new idea: do breadth first search for each node until reaching a terminal node. Ignore nodes that have already been visited in the current search (reasoning: taking a circular dependency won't be shorter). On second thought, this might not work because of the alternating between min/max of depths of children.

Another idea: pretty much the previous idea, but with depth first search (so ignore nodes already visited in order to get to the current node). This seems to be working, although the way I'm currently tracking visited nodes seems inefficient (as I copy the set at each iteration). Thinking of checking out persistent data structures.

## Useful work

Generating code from ANTLR v4 grammars:
https://github.com/renatahodovan/grammarinator
(and the accompanying paper, "Grammarinator: A Grammar-Based Open Source Fuzzer", although it doesn't provide much insight)

Generate code and mutate test cases (precedes grammarinator):
"Fuzzing with Code Fragments" resulting in LangFuzz, however not open source.
https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final73.pdf

Generating code from grammars very quickly:
"Building Fast Fuzzers" resulting in F1 fuzzer, however not very useful. Not many options, unclear whether being fast is useful for us.
https://arxiv.org/pdf/1911.07707.pdf