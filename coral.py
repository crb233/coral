'''
The Coral Interpreter
Written by Curtis Bechtel
'''

from queue import Queue





########################
# Tokenizer and Parser #
########################

whitespace = {' ', '\n', '\t'}
symbols = {'(', ')', '=', '#'}
non_word = symbols.union(whitespace)

class State:
    pass

class ParseType:
    '''Which type of token are we parsing'''
    LEFT = 0   # the left hand side of a rule
    RIGHT = 1  # the riht hand side of a rule
    INPUT = 2  # an input term to be reduced

class Token:
    '''Basic token class'''
    def __init__(self, val, file, row, col):
        self.val = val
        self.file = file
        self.line = row + 1   # convert from 0 to 1-based indexing
        self.col = col + 1
    def __str__(self):
        return self.val

class EndLineToken(Token):
    pass

class SymbolToken(Token):
    pass

class AtomToken(Token):
    pass

class VariableToken(Token):
    pass

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
        return EndLineToken('\n', filename, state.r, state.c)
    
    # check for special symbols
    for sym in symbols:
        if line.startswith(sym, state.c):
            tok = SymbolToken(sym, filename, state.r, state.c)
            state.c += len(sym)
            return tok
    
    # tokenize a word
    i = state.c
    while i < len(line) and line[i] not in non_word:
        i += 1
    
    # determine if word is an atom or variable
    word = line[state.c:i]
    if word[0].isupper():
        tok = VariableToken(word, filename, state.r, state.c)
    else:
        tok = AtomToken(word, filename, state.r, state.c)
    
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
    tokens.append(EndLineToken('\n', filename, state.r, 0))
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

def unexpected(tok=None):
    '''Creates a SyntaxError for unexpected tokens'''
    if isinstance(tok, EndLineToken):
        return SyntaxError("Unexpected end of line", tok.file, tok.line, tok.col)
    else:
        return SyntaxError("Unexpected token '{}'".format(tok.val), tok.file, tok.line, tok.col)

def parse_term(tokens, type, state=None):
    '''Parses a single term from a list of tokens.
    
    This method starts with the token at index i and attempts to parse a term of
    the given type. Valid types include LEFT for left-hand side terms, RIGHT for
    right-hand terms, and INPUT for user-input terms'''
    
    if state is None:
        state = State()
        state.i = 0
    
    chain = []
    group = []
    
    while state.i < len(tokens):
        tok = tokens[state.i]
        
        if isinstance(tok, AtomToken):
            group.append(tok.val)
            
        elif type == ParseType.LEFT and len(group) == 0:
            # first term on the left must be an atom
            raise unexpected(tok)
            
        elif isinstance(tok, VariableToken):
            if type == ParseType.INPUT:
                raise unexpected(tok)
            group.append(tok.val)
            
        elif isinstance(tok, EndLineToken):
            if len(chain) == 0 and type != ParseType.LEFT:
                break
            elif len(chain) == 0:
                raise unexpected(tok)
            
        elif tok.val == '=':
            if len(chain) == 0 and type == ParseType.LEFT:
                break
            else:
                raise unexpected(tok)
            
        elif tok.val == '(':
            g = []
            group.append(g)
            chain.append(group)
            group = g
            
        elif tok.val == ')':
            if len(chain) == 0 or len(group) == 0:
                raise unexpected(tok)
            group = chain.pop()
            
        else:
            raise Exception('Parser error')
        
        state.i += 1
    
    if len(chain) > 0 or len(group) == 0:
        raise unexpected(tokens[-1])
    
    if len(group) == 1:
        return simplify(group[0])
    
    return simplify(group)

def parse_rules(tokens, rules):
    '''Parses a set of rules and adds them to the ruleset'''
    
    state = State()
    state.i = 0
    while state.i < len(tokens):
        # skip newlines
        while state.i < len(tokens) and isinstance(tokens[state.i], EndLineToken):
            state.i += 1
        
        if state.i == len(tokens):
            break
        
        lhs = parse_term(tokens, ParseType.LEFT, state)
        state.i += 1
        
        rhs = parse_term(tokens, ParseType.RIGHT, state)
        state.i += 1
        
        key = keyword(lhs)
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





###################
# Virtual Machine #
###################

def isatom(term):
    return isinstance(term, str) and not term[0].isupper()

def isvar(term):
    return isinstance(term, str) and term[0].isupper()

def isapp(term):
    return isinstance(term, list)

def clone(term):
    if isatom(term) or isvar(term):
        return term
    
    else:
        return [clone(child) for child in term]

def stringify(term, inner=False):
    if isatom(term) or isvar(term):
        return term
    
    elif inner:
        return '(' + ' '.join([stringify(child, True) for child in term]) + ')'
    
    else:
        return ' '.join([stringify(child, True) for child in term])

def keyword(term):
    if isatom(term):
        return term
    
    else:
        return term[0]

def replace(term, table):
    '''Replaces variabes with their values from the table'''
    
    if isatom(term):
        return term
    
    elif isvar(term):
        return clone(table[term])
    
    else:
        for i in range(len(term)):
            term[i] = replace(term[i], table)
        return term

def match(pattern, term, table=None):
    '''Attempts to match a pattern to a term, adding variable values to the
    table as necessary. Returns True if the terms match and False otherwise'''
    
    if table is None: table = {}
    
    if isatom(pattern):
        return isatom(term) and pattern == term
    
    elif isvar(pattern):
        if pattern in table:
            return table[pattern] == term
        table[pattern] = term
        return True
    
    else:
        if isatom(term):
            return pattern[0] == term
        if len(pattern) > len(term):
            return False
        for a, b in zip(pattern, term):
            if not match(a, b, table):
                return False
        return True

def simplify(term):
    if isapp(term) and isapp(term[0]):
        new = simplify(term[0])
        new.extend(term[1:])
        return new
    
    elif isapp(term) and len(term) == 1:
        return simplify(term[0])
    
    else:
        return term

def reduce(term, rules):
    '''Attempts to reduce a term with the given ruleset. If it succeeds, return
    the new term. Otherwise, return None.'''
    
    if isvar(term):
        return None
        
    elif isatom(term):
        if term in rules:
            for lhs, rhs in rules[term]:
                if match(lhs, term):
                    return clone(rhs)
        return None
        
    elif term[0] not in rules:
        return None
        
    else:
        for lhs, rhs in rules[term[0]]:
            table = {}
            if match(lhs, term, table):
                if isatom(lhs):
                    term[0] = clone(rhs)
                    return simplify(term)
                elif isatom(rhs) or isvar(rhs):
                    res = [clone(rhs)]
                    res.extend(term[len(lhs):])
                    return simplify(replace(res, table))
                else:
                    res = clone(rhs)
                    res.extend(term[len(lhs):])
                    return simplify(replace(res, table))
        
        return None

def full_reduce(root_term, rules):
    '''Reduces the term until no more rules can be applied.
    
    This function will traverse the tree of terms breadth-wise until a single
    term can be reduced. Then it will start again at the top of the tree. When
    it runs out of terms to reduce, the initial term is considered fully reduced
    and is returned'''
    
    queue = Queue()
    queue.put((root_term, None, None))
    
    while not queue.empty():
        term, parent, index = queue.get()
        reduced = reduce(term, rules)
        
        if reduced is None:
            if isapp(term):
                for i in range(1, len(term)):
                    queue.put((term[i], term, i))
            
        else:
            if parent is None:
                root_term = reduced
            else:
                parent[index] = reduced
            queue = Queue()
            queue.put((root_term, None, None))
        
    return root_term





########
# Main #
########

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
            term = parse_term(tokens, ParseType.INPUT)
            term = full_reduce(term, rules)
            print(stringify(term))
        except SyntaxError as err:
            print(err)

if __name__ == "__main__":
    from sys import argv
    main(argv[1:])
