import re
from enum import Enum, auto
from collections import namedtuple
from random import randrange, choice

from antlr4 import CommonTokenStream, FileStream, ParserRuleContext

from antlr_stuff.compiled.ANTLRv4Parser import ANTLRv4Parser
from antlr_stuff.compiled.ANTLRv4Lexer import ANTLRv4Lexer

from charset_parser import lexer_charset_interval
from unicode_range import ranges_to_list, printable_unicode_ranges, printable_unicode_ranges_list

class NodeType(Enum):
	ROOT = auto()
	PARSER_RULE = auto()
	LEXER_RULE = auto()
	RULE_REF = auto()
	TOKEN_REF = auto()
	QUANTIFIER = auto()
	ALTERNATIVES = auto()
	ALTERNATIVE = auto()
	STRING_LITERAL = auto()
	CHAR_SET = auto()
	NOT = auto()
	DOT = auto()

LEAF_TYPES = [
	NodeType.RULE_REF,
	NodeType.TOKEN_REF,
	NodeType.STRING_LITERAL,
	NodeType.CHAR_SET,
	NodeType.DOT
]

Node = namedtuple('Node', ['type', 'value'])
Graph = namedtuple('Graph', ['nodes', 'edges', 'parser_rules', 'lexer_rules'])

def build_graph(rule):
	nodes = []
	edges = []

	parser_rules = {}
	lexer_rules = {}

	def add_node(node):
		nodes.append(node)
		edges.append([])
		return len(nodes) - 1

	def add_edge(parent, child):
		edges[parent].append(child)

	def add_child(parent_id, child):
		child_id = add_node(child)
		add_edge(parent_id, child_id)
		return child_id

	def add_children(rule, node):
		if rule.getChildCount():
			for child in rule.children:
				_build_graph(child, node)

	def _build_graph(rule, parent):
		if isinstance(rule, ANTLRv4Parser.ParserRuleSpecContext):
			node = Node(NodeType.PARSER_RULE, str(rule.RULE_REF()))
			node_id = add_child(parent, node)
			add_children(rule, node_id)

			parser_rules[str(rule.RULE_REF())] = node_id

		elif isinstance(rule, ANTLRv4Parser.LexerRuleSpecContext):
			node = Node(NodeType.LEXER_RULE, str(rule.TOKEN_REF()))
			node_id = add_child(parent, node)
			add_children(rule, node_id)

			lexer_rules[str(rule.TOKEN_REF())] = node_id

		elif isinstance(rule, (ANTLRv4Parser.ElementContext, ANTLRv4Parser.LexerElementContext)):
			# TODO: Make sure this works with +? and *? and +? and ??
			suffix = None
			if rule.ebnfSuffix():
				suffix = rule.ebnfSuffix()
			elif hasattr(rule, 'ebnf') and rule.ebnf() and rule.ebnf().blockSuffix():
				suffix = rule.ebnf().blockSuffix().ebnfSuffix()

			if suffix:
				node = Node(NodeType.QUANTIFIER, str(suffix.children[0]))
				node_id = add_child(parent, node)
				add_children(rule, node_id)
			else:
				_build_graph(rule.children[0], parent)

		elif isinstance(rule, ANTLRv4Parser.RulerefContext):
			node = Node(NodeType.RULE_REF, str(rule.RULE_REF()))
			add_child(parent, node)

		elif isinstance(rule, ANTLRv4Parser.TerminalContext):
			if rule.TOKEN_REF():
				node = Node(NodeType.TOKEN_REF, str(rule.TOKEN_REF()))
				add_child(parent, node)
			elif rule.STRING_LITERAL():
				node = Node(NodeType.STRING_LITERAL, str(rule.STRING_LITERAL())[1:-1])
				add_child(parent, node)

		elif isinstance(rule, (ANTLRv4Parser.RuleAltListContext, ANTLRv4Parser.LexerAltListContext)):
			node = Node(NodeType.ALTERNATIVES, None)
			node_id = add_child(parent, node)
			add_children(rule, node_id)

		elif isinstance(rule, ANTLRv4Parser.LabeledAltContext):
			label = None
			if rule.identifier() and (rule.identifier().TOKEN_REF() or rule.identifier().RULE_REF()):
				label = str(rule.identifier().TOKEN_REF() or rule.identifier().RULE_REF())

			node = Node(NodeType.ALTERNATIVE, label)
			node_id = add_child(parent, node)
			add_children(rule.alternative(), node_id)

		elif isinstance(rule, ANTLRv4Parser.LexerAltContext):
			node = Node(NodeType.ALTERNATIVE, None)
			node_id = add_child(parent, node)
			add_children(rule.lexerElements(), node_id)

		elif isinstance(rule, (ANTLRv4Parser.AtomContext, ANTLRv4Parser.LexerAtomContext)):
			lexer_atom = isinstance(rule, ANTLRv4Parser.LexerAtomContext)

			if rule.DOT():
				node = Node(NodeType.DOT, None)
				add_child(parent, node)
			elif rule.notSet():
				node = Node(NodeType.NOT, None)
				node_id = add_child(parent, node)
				add_children(rule.notSet(), node_id)
			elif lexer_atom and rule.characterRange():
				start = ord(str(rule.characterRange().children[0])[1:-1])
				end = ord(str(rule.characterRange().children[2])[1:-1]) + 1
				node = Node(NodeType.CHAR_SET, [(start, end)])
				add_child(parent, node)
			elif lexer_atom and rule.LEXER_CHAR_SET():
				char_set = lexer_charset_interval(str(rule.LEXER_CHAR_SET())[1:-1])
				node = Node(NodeType.CHAR_SET, char_set)
				add_child(parent, node)
			else:
				add_children(rule, parent)

		elif isinstance(rule, ANTLRv4Parser.SetElementContext):
			if rule.TOKEN_REF():
				node = Node(NodeType.TOKEN_REF, str(rule.TOKEN_REF()))
				add_child(parent, node)
			elif rule.STRING_LITERAL():
				string_value = bytes(str(rule.STRING_LITERAL())[1:-1], 'utf-8').decode('unicode_escape')
				node = Node(NodeType.STRING_LITERAL, string_value)
				add_child(parent, node)
			elif rule.characterRange():
				start = ord(str(rule.characterRange().children[0])[1:-1])
				end = ord(str(rule.characterRange().children[2])[1:-1]) + 1
				node = Node(NodeType.CHAR_SET, [(start, end)])
				add_child(parent, node)
			elif rule.LEXER_CHAR_SET():
				char_set = lexer_charset_interval(str(rule.LEXER_CHAR_SET())[1:-1])
				node = Node(NodeType.CHAR_SET, char_set)
				add_child(parent, node)

		elif isinstance(rule, ParserRuleContext):
			add_children(rule, parent)

	root_id = add_node(Node(NodeType.ROOT, None))
	_build_graph(rule, root_id)

	return Graph(nodes, edges, parser_rules, lexer_rules)

def graph_to_str(graph):
	out = ''

	nodes = graph.nodes
	edges = graph.edges

	def _s(node_id, depth):
		nonlocal out
		node = nodes[node_id]
		indent = depth * '| '
		out += indent + node.type.name + ' ' + str(node.value) + '\n'

		for child_id in edges[node_id]:
			_s(child_id, depth + 1)

	_s(0, 0)
	return out

def calculate_depths(graph):
	nodes = graph.nodes
	edges = graph.edges
	parser_rules = graph.parser_rules
	lexer_rules = graph.lexer_rules

	depths = [None] * len(nodes)

	def _calc(node_id, visited_node_ids):
		if depths[node_id] is not None:
			return depths[node_id]

		if node_id in visited_node_ids:
			return float('inf')

		node = nodes[node_id]

		new_visited_node_ids = visited_node_ids.copy()
		new_visited_node_ids.add(node_id)

		children_ids = None
		if node.type == NodeType.RULE_REF:
			children_ids = [parser_rules[node.value]]
		elif node.type == NodeType.TOKEN_REF:
			if node.value == 'EOF':
				children_ids = []
			else:
				children_ids = [lexer_rules[node.value]]
		else:
			children_ids = edges[node_id]

		if len(children_ids) == 0:
			return 0

		if node.type == NodeType.QUANTIFIER and node.value in ('?', '*'):
			return 0

		if node.type in (NodeType.ALTERNATIVES, NodeType.ROOT):
			depth = float('inf')

			for child_id in children_ids:
				child_depth = _calc(child_id, new_visited_node_ids)

				if child_depth < depth:
					depth = child_depth

			return depth + 1

		depth = 0

		for child_id in children_ids:
			child_depth = _calc(child_id, new_visited_node_ids)

			if child_depth > depth:
				depth = child_depth

		return depth + 1

	for node_id in range(len(nodes)):
		depths[node_id] = _calc(node_id, set())

	return depths

def generate_from_graph(graph, start_rule, max_total_depth, ranges, depths):
	assert start_rule in graph.parser_rules.keys()

	out = ''

	nodes = graph.nodes
	edges = graph.edges
	parser_rules = graph.parser_rules
	lexer_rules = graph.lexer_rules

	def _gen(node_id, max_depth):
		nonlocal out
		node = nodes[node_id]
		children_ids = edges[node_id]

		if node.type == NodeType.RULE_REF:
			_gen(parser_rules[node.value], max_depth - 1)
		elif node.type == NodeType.TOKEN_REF:
			if node.value != 'EOF':
				_gen(lexer_rules[node.value], max_depth - 1)
		elif node.type == NodeType.STRING_LITERAL:
			out += node.value
		elif node.type == NodeType.DOT:
			out += chr(choice(printable_unicode_ranges_list))
		elif node.type == NodeType.CHAR_SET:
			if node_id not in ranges:
				ranges[node_id] = ranges_to_list(node.value)

			out += chr(choice(ranges[node_id]))
		elif node.type == NodeType.NOT:
			if node_id not in ranges:
				set_to_not = set()

				for child_id in children_ids:
					child = nodes[child_id]

					if child.type == NodeType.STRING_LITERAL:
						assert len(child.value) == 1, 'String literal in NOT can only have a single character'
						set_to_not.add(ord(child.value))
					elif child.type == NodeType.CHAR_SET:
						set_to_not.update(ranges_to_list(child.value))
					else:
						raise Exception('Unhandled NOT child type', child.type)

				negated_sets = set(printable_unicode_ranges_list) - set_to_not
				ranges[node_id] = list(negated_sets)

			out += chr(choice(ranges[node_id]))
		elif node.type == NodeType.ALTERNATIVES:
			filtered_children_ids = list(filter(
				lambda i: depths[i] <= max_depth,
				children_ids
			))
			num_children = len(filtered_children_ids)

			if num_children > 0:
				_gen(filtered_children_ids[randrange(num_children)], max_depth - 1)
		elif node.type == NodeType.QUANTIFIER:
			quant = node.value

			if quant == '?':
				if randrange(2) == 0:
					for child_id in children_ids:
						_gen(child_id, max_depth - 1)
			elif quant in ('+', '*'):
				if quant == '+':
					for child_id in children_ids:
						_gen(child_id, max_depth - 1)

				while randrange(2) == 0:
					for child_id in children_ids:
						_gen(child_id, max_depth - 1)
		else:
			for child_id in children_ids:
				_gen(child_id, max_depth - 1)

	_gen(parser_rules[start_rule], max_total_depth)

	return out

def generate(grammar_file, start_rule, iterations, max_depth):
	antlr_parser = ANTLRv4Parser(CommonTokenStream(ANTLRv4Lexer(FileStream(grammar_file, encoding='utf-8'))))
	current_root = antlr_parser.grammarSpec()
	graph = build_graph(current_root)

	ranges = {}
	depths = calculate_depths(graph)

	for n in range(iterations):
		yield generate_from_graph(graph, start_rule, max_depth, ranges, depths)
