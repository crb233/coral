
'''
The Coral Interpreter
Written by Curtis Bechtel
Inspired by the Anemone language

Coral is a functional language based on pattern-matching and term-rewriting. In
appearance, Coral is similar to languages like Lisp, Scheme, and Clojure, but
it functions very differently. Rather than applying functions to literals, it
takes a group of atoms (literals) and reduces it according to a user-defined set
of rules.

All statements in Coral are written as follows:
    <pattern> = <result>

This statement can be read as "<pattern> yields <result>". It represents a
single reduction rule that the interpreter can apply to a term. Rules can only
be loaded into the interpreter from files (libraries).

The only datatype in Coral is the atom. Integers, floats, lists, and other
high-order data types must be simulated by groups of atoms and rules.

For example, the file math.coral might contain:
    
    zero = 0
    one = s 0
    two = s (s 0)
    three = s (s (s 0))
    
    + A 0 = A
    + A (s B) = + (s A) B
    
    * A 0 = 0
    * A (s B) = + A (* A B)
    
We can then load this file into the interpreter and give it terms to reduce:
    >>> * two three
    (s (s (s (s (s (s 0))))))
    >>> + three one
    (s (s (s (s 0))))
    >>> * two zero
    0

'''

from queue import Queue

ATOM = 0
VAR = 1
GROUP = 2

class Term:
    '''An atom, variable, or aplication group'''
    def __init__(self, val, type):
        self.val = val
        self.type = type
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        if is_atom(self) or is_var(self):
            return self.val
        return '(' + ' '.join(map(str, self.val)) + ')'

def is_atom(term):
    return term.type == ATOM

def is_var(term):
    return term.type == VAR

def is_group(term):
    return term.type == GROUP

def clone(term):
    '''Creates and returns a deep clone of a term'''
    if is_atom(term):
        return Term(term.val, ATOM)
    elif is_var(term):
        return Term(term.val, VAR)
    else:
        return Term([clone(child) for child in term.val], GROUP)

def replace(term, table):
    '''Replaces all variables with their respective terms from the table'''
    if is_atom(term):
        return term
    elif is_var(term):
        return clone(table[term.val])
    else:
        term.val = [replace(child, table) for child in term.val]
        return term

def match(pattern, term, table):
    '''Attempts to match a term to a given patten (a term with variables)'''
    if is_atom(pattern):
        return is_atom(term) and pattern.val == term.val
    elif is_var(pattern):
        if pattern.val in table:
            return term.val == table[pattern.val]
        
        table[pattern.val] = term
        return True
    else:
        if not is_group(term) or len(pattern.val) != len(term.val):
            return False
        
        for a, b in zip(pattern.val, term.val):
            if not match(a, b, table):
                return False
        
        return True

def reduce(term, rules):
    '''Attempts to reduce a term with the given ruleset. If it succeeds, return
    the new term. Otherwise, return None.'''
    
    if is_var(term):
        return None
        
    elif is_atom(term):
        if term.val in rules:
            for lhs, rhs in rules[term.val]:
                if match(lhs, term, {}):
                    return clone(rhs)
        return None
        
    else:
        if len(term.val) == 0 or not is_atom(term.val[0]):
            return None
        
        first = term.val[0]
        if first.val == 'print' and len(term.val) == 2:
            print(str(term.val[1]))
            return term.val[1]
        
        elif first.val in rules:
            for lhs, rhs in rules[first.val]:
                table = {}
                if match(lhs, term, table):
                    return replace(clone(rhs), table)
        return None

def full_reduce(initial_term, rules):
    '''Reduces the term until no more rules can be applied.
    
    This function will traverse the tree of terms breadth-wise until a single
    term can be reduced. Then it will start again at the top of the tree. When
    it runs out of terms to reduce, the initial term is considered fully reduced
    and is returned'''
    
    queue = Queue()
    queue.put(initial_term)
    while not queue.empty():
        term = queue.get()
        res = reduce(term, rules)
        if res is None:
            if is_group(term):
                for child in term.val:
                    queue.put(child)
        else:
            term.val = res.val
            term.type = res.type
            queue = Queue()
            queue.put(initial_term)
    return initial_term

class Token:
    '''Basic token class'''
    def __init__(self, val, file, row, col):
        self.val = val
        self.file = file
        self.line = row + 1   # convert from 0 to 1-based indexing
        self.col = col + 1
    def __str__(self):
        return self.val

class NewLine(Token):
    pass

class Symbol(Token):
    pass

class Atom(Token):
    pass

class Variable(Token):
    pass

class State:
    pass

whitespace = {' ', '\n', '\t'}
symbols = {'(', ')', '=', '#'}
non_word = symbols.union(whitespace)

def next_token(line, state, filename):
    '''Read one token from the line, given the current tokenization state'''
    
    # remove leading whitespace
    while state.c < len(line) and line[state.c] in whitespace:
        state.c += 1
    
    # remove comments
    if state.c < len(line) and line[state.c] == '#':
        state.c = len(line)
    
    # check for the end of the line
    if state.c == len(line):
        return NewLine('\n', filename, state.r, state.c)
    
    # check for special symbols
    for sym in symbols:
        if line.startswith(sym, state.c):
            tok = Symbol(sym, filename, state.r, state.c)
            state.c += len(sym)
            return tok
    
    # tokenize a word
    i = state.c
    while i < len(line) and line[i] not in non_word:
        i += 1
    
    # determine if word is an atom or variable
    word = line[state.c:i]
    if word[0].isupper():
        tok = Variable(word, filename, state.r, state.c)
    else:
        tok = Atom(word, filename, state.r, state.c)
    
    state.c = i
    return tok

def tokenize(f, filename):
    '''Tokenize a file stream with the given name'''
    tokens = []
    state = State()
    state.r = 0
    for line in f:
        state.c = 0
        while state.c < len(line):
            tokens.append(next_token(line, state, filename))
        state.r += 1
    tokens.append(NewLine('\n', filename, state.r, 0))
    return tokens

class SyntaxError(Exception):
    '''Custom syntax error'''
    def __init__(self, msg, file, line, col):
        self.msg = msg
        self.file = file
        self.line = line
        self.col = col
    def __str__(self):
        return "{} at {}:{} in '{}'".format(self.msg, self.line, self.col, self.file)

def unexpected(tok):
    '''Creates a SyntaxError for unexpected tokens'''
    if isinstance(tok, NewLine):
        return SyntaxError("Unexpected end of line", tok.file, tok.line, tok.col)
    else:
        return SyntaxError("Unexpected token '{}'".format(tok.val), tok.file, tok.line, tok.col)

LEFT = 0
RIGHT = 1
INPUT = 2

def parse_term(tokens, type, i=0):
    '''Parses a single term from a list of tokens.
    
    This method starts with the token at index i and attempts to parse a term of
    the given type. Valid types include LEFT for left-hand side terms, RIGHT for
    right-hand terms, and INPUT for user-input terms'''
    
    chain = []
    group = Term([], GROUP)
    
    while i < len(tokens):
        tok = tokens[i]
        
        if isinstance(tok, Atom):
            group.val.append(Term(tok.val, ATOM))
            
        elif type == LEFT and len(group.val) == 0:
            # first term on the left must be an atom
            raise unexpected(tok)
            
        elif isinstance(tok, Variable):
            if type == INPUT:
                raise unexpected(tok)
            group.val.append(Term(tok.val, VAR))
            
        elif isinstance(tok, NewLine):
            if len(chain) == 0 and type != LEFT:
                break
            elif len(chain) == 0:
                raise unexpected(tok)
            
        elif tok.val == '=':
            if len(chain) == 0 and type == LEFT:
                break
            else:
                raise unexpected(tok)
            
        elif tok.val == '(':
            g = Term([], GROUP)
            group.val.append(g)
            chain.append(group)
            group = g
            
        elif tok.val == ')':
            if len(chain) == 0 or len(group.val) == 0:
                raise unexpected(tok)
            group = chain.pop()
            
        else:
            raise Exception('Parser error')
        
        i += 1
    
    if len(chain) > 0 or len(group.val) == 0:
        raise unexpected(tokens[-1])
    elif len(group.val) == 1:
        return group.val[0], i
    else:
        return group, i

def parse_rules(tokens, rules):
    '''Parses a set of rules and adds them to the ruleset'''
    
    i = 0
    while i < len(tokens):
        # skip newlines
        while i < len(tokens) and isinstance(tokens[i], NewLine):
            i += 1
        
        if i == len(tokens):
            break
        
        lhs, i = parse_term(tokens, LEFT, i)
        i += 1
        
        rhs, i = parse_term(tokens, RIGHT, i)
        i += 1
        
        key = lhs.val if is_atom(lhs) else lhs.val[0].val
        if key in rules:
            rules[key].append((lhs, rhs))
        else:
            rules[key] = [(lhs, rhs)]
    
    return rules

def load(filename, rules=None):
    '''Loads the rules from a file into the given ruleset'''
    if rules is None:
        rules = {}
    
    if not filename.endswith('.coral'):
        filename += '.coral'
    
    with open(filename, "r") as f:
        tokens = tokenize(f, filename)
    
    try:
        parse_rules(tokens, rules)
        return rules
    except SyntaxError as err:
        print(err)

def main(args):
    '''Starts the interpreter'''
    
    from io import StringIO
    
    # load libraries
    rules = {}
    for name in args:
        load(name, rules)
    
    while 1:
        print("> ", end="")
        inp = input()
        
        # check for special input
        if inp in ['exit', 'quit']:
            break
            
        # reload all libraries
        elif inp == 'reload':
            rules = {}
            for name in args:
                load(name, rules)
        
        # TODO allow multiline input while parentheses are valid and unmatched
        
        # try parsing and simplifying the entered term
        try:
            tokens = tokenize(StringIO(inp), '<stdin>')
            term, i = parse_term(tokens, INPUT)
            term = full_reduce(term, rules)
            print(term)
        except SyntaxError as err:
            print(err)

if __name__ == "__main__":
    from sys import argv
    main(argv[1:])
