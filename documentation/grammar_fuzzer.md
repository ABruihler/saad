# Grammar Fuzzer

This document gives a brief outline of the grammar fuzzer included with SAAD. More information can be found in the [grammar fuzzer README](../scripts/probes/grammar_fuzzer/README.md).

The code is located in [scripts/probes/grammar_fuzzer/](../scripts/probes/grammar_fuzzer/) and was originally developed in a separate repo (so look there for a more complete commit history): https://github.com/skimberk/first-fuzzer

An example repository which uses the grammar fuzzer can be found here: https://github.com/skimberk/saad_fuzzer_example. This example fuzzes a very simple calculator language interpreter.

The grammar fuzzer module (named `grammarFuzz`) takes three arguments:

1. `grammarFile`: The path of the ANTLR4 grammar file from which to generate input. See below for more info regarding this format and what features are supported.

2. `entryRule`: The name of the "root" ANTLR rule (from the `grammarFile`). This is the rule from which the fuzzer will generate input.

3. `executeFile`: The path of the file which will be executed by the fuzzer. The generated input will be piped in via STDIN. The file will be executed once for every generated input. The file should be executable (you might have to run `chmod +x <filename>` to flag it as executable).

Here's an example probe using this module (taken from the example repo):
```json
[
  {
    "name": "fuzzOutput",
    "type": "grammarFuzz",
    "config": {
      "grammarFile": "POSTFIX_CALC.g4",
      "entryRule": "expr",
      "executeFile": "postfix_calculator.py"
    }
  },
  {
    "type": "slackBotSimple",
    "config": {
      "channel": "monitoring-slack-test-public",
      "message": "{fuzzOutput}"
    }
  }
]
```

## Module Output

The fuzzer keeps track of all inputs which cause `executeFile` to exit with a non-zero return code. It then logs all these inputs along with the resulting STDOUT and STDERR.

## Iterations and Max Depth

The fuzzer (which is run by the module) allows for configuration of the number of iterations (the number of inputs that will be generated, and, by extension, the number of times `executeFile` will get executed). It also allows for configuration of the generated input maximum depth: the fuzzer works by building a graph from the `grammarFile` and randomly traveling through this graph, starting from the node specified in `entryRule`.

Hypothetically, we could travel infinitely far through this graph (as it might have cycles), however this would lead to a stack overflow. By setting a maximum depth, we limit how far we travel through the graph.

These values are *not* currently configurable in the `grammarFuzz` module, however it would be trivial to add these options (simply add two new arguments which set the `--iterations` and `--max_depth` command line arguments). The default value for `--iterations` is `100` and the default value for `--max_depth` is `500`.

## ANTLR Format

The fuzzer accepts grammar definition in the ANTLR4 format.

ANTLR is "a powerful parser generator for reading, processing, executing, or translating structured text or binary files" (this description is taken from the ANTLR4 Github: https://github.com/antlr/antlr4). 

It has a great syntax for specifying grammars, so, instead of reinventing the wheel, we support a simplified version of this syntax. This is especially useful as there is a large wealth of ANTLR4 grammars already written. We can find grammars for most popular programming languages here: https://github.com/antlr/grammars-v4. Unfortunately, most of these likely won't work as-is as they use actions or other complex ANTLR features, however the [JSON](https://github.com/antlr/grammars-v4/blob/master/json/JSON.g4) and [S-expression](https://github.com/antlr/grammars-v4/blob/master/sexpression/sexpression.g4) grammars work as-is.

Here's a simple supported grammar definition (used in the example repo) for a postfix calculator language:
```ANTLR
grammar POSTFIX_CALC;

expr
   : NUMBER
   | expr ' ' expr ' ' OPERATOR;

OPERATOR : '+' | '-' | '*';
// OPERATOR : '+' | '-' | '*' | '/'; // This allows division by zero!


// Borrowed from JSON.g4 from antlr4-grammars/

NUMBER
   : '-'? INT ('.' [0-9] +)? EXP?
   ;


fragment INT
   : '0' | [1-9] [0-9]*
   ;

// no leading zeros

fragment EXP
   : [Ee] [+\-]? INT
   ;
```

## Attribution

The grammar fuzzer was developed by Sebastian Kimberk. It is heavily inspired by the open source [grammarinator](https://github.com/renatahodovan/grammarinator) project by Renáta Hodován.
