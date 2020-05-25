# Grammar Fuzzer

This document gives a brief outline of the grammar fuzzer included with SAAD. More information can be found in the [grammar fuzzer README](../scripts/probes/grammar_fuzzer/README.md).

The code is located in [scripts/probes/grammar_fuzzer/](../scripts/probes/grammar_fuzzer/) and was originally developed in a separate repo (so look there for a more complete commit history): https://github.com/skimberk/first-fuzzer

An example repository which uses the grammar fuzzer can be found here: https://github.com/skimberk/saad_fuzzer_example. This example fuzzes a very simple calculator language interpreter.

The grammar fuzzer module (named `grammarFuzz`) takes three arguments:

1. `grammarFile`: The path of the ANTLRv4 grammar file from which to generate input. See below for more info regarding this format and what features are supported.

2. `entryRule`: The name of the "root" ANTLR rule (from the `grammarFile`). This is the rule from which the fuzzer will generate input.

3. `executeFile`: The path of the file which will be executed by the fuzzer. The generated input will be piped in via STDIN. The file will be executed once for every generated input. The file should be executable (you might have to run `chmod +x <filename>` to mark it executable).

The fuzzing script allows for configuration of the number of iterations (the number of inputs that will be generated, and, by extension, the number of times `executeFile` will get executed). It also allows for configuration of the generated input maximum depth: the fuzzer works by building a graph from the `grammarFile` and randomly traveling through this graph, starting from the node specified in `entryRule`. Hypothetically, we could travel infinitely far through this graph (as it might have cycles), however this would lead to a stack overflow. By setting a maximum depth, we limit how far we travel through the graph. These values are *not* currently configurable in the `grammarFuzz` module, however it would be trivial to add these options (simply add two new arguments which set the `--iterations` and `--max_depth` command line arguments). The default value for `--iterations` is `100` and the default value for `--max_depth` is `500`.