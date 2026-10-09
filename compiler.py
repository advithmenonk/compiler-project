import re

# =====================================================================
# 1. AST NODES
# =====================================================================
class Node: 
    pass

class Num(Node):
    def __init__(self, v): 
        self.v = int(v)

class Var(Node):
    def __init__(self, n): 
        self.n = n

class BinOp(Node):
    def __init__(self, l, op, r): 
        self.l, self.op, self.r = l, op, r

class Assign(Node):
    def __init__(self, target, expr): 
        self.target, self.expr = target, expr


# =====================================================================
# 2. LEXER
# =====================================================================
def tokenize(text):
    pattern = r'[a-zA-Z_]\w*|\d+|[=+\-*/()]'
    tokens, pos = [], 0
    while pos < len(text):
        if text[pos].isspace(): 
            pos += 1
            continue
        match = re.match(pattern, text[pos:])
        if not match: 
            raise Exception(f"Lexical Error: Invalid character '{text[pos]}'")
        token = match.group()
        tokens.append(token)
        pos += len(token)
    return tokens

def classify_tokens(tokens):
    res = []
    for t in tokens:
        if t.isdigit(): 
            res.append((t, "NUMBER"))
        elif re.match(r'^[a-zA-Z_]\w*$', t): 
            res.append((t, "IDENTIFIER"))
        elif t == '=': 
            res.append((t, "ASSIGNMENT"))
        else: 
            res.append((t, "OPERATOR"))
    return res


# =====================================================================
# 3. PARSER (Recursive Descent)
# =====================================================================
class Parser:
    def __init__(self, tokens): 
        self.tokens, self.pos = tokens, 0

    def peek(self): 
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def get(self):
        t = self.peek()
        if t is None: 
            raise Exception("Syntax Error: Unexpected end of input")
        self.pos += 1
        return t

    def parse(self):
        if not self.tokens: 
            raise Exception("Syntax Error: Empty input")
        if len(self.tokens) > 1 and self.tokens[1] == '=':
            target = self.get()
            self.get() # Consume '='
            return Assign(target, self.expr())
        return self.expr()

    def expr(self):
        node = self.term()
        while self.peek() in ('+', '-'): 
            op = self.get()
            node = BinOp(node, op, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() in ('*', '/'): 
            op = self.get()
            node = BinOp(node, op, self.factor())
        return node

    def factor(self):
        t = self.get()
        if t == '(':
            node = self.expr()
            if self.peek() != ')': 
                raise Exception("Syntax Error: Missing ')'")
            self.get() # Consume ')'
            return node
        if t == ')': 
            raise Exception("Syntax Error: Unexpected ')'")
        if t.isdigit(): 
            return Num(t)
        if re.match(r'^[a-zA-Z_]\w*$', t): 
            return Var(t)
        raise Exception(f"Syntax Error: Unexpected token '{t}'")


# =====================================================================
# 4. SYMBOL TABLE & SEMANTIC CHECKER
# =====================================================================
def build_symbol_table(node, table):
    if isinstance(node, Var): 
        table[node.n] = "int"
    elif isinstance(node, Assign): 
        table[node.target] = "int"
        build_symbol_table(node.expr, table)
    elif isinstance(node, BinOp): 
        build_symbol_table(node.l, table)
        build_symbol_table(node.r, table)

def semantic_check(node):
    if isinstance(node, Assign):
        if not re.match(r'^[a-zA-Z_]\w*$', node.target): 
            raise Exception("Semantic Error: Invalid variable name")
        semantic_check(node.expr)
    elif isinstance(node, BinOp):
        semantic_check(node.l)
        semantic_check(node.r)
        if node.op == '/' and isinstance(node.r, Num) and node.r.v == 0:
            raise Exception("Semantic Error: Division by zero")


# =====================================================================
# 5. AST DISPLAY UTIL
# =====================================================================
def print_ast(node, level=0):
    space = "  " * level
    if isinstance(node, Num): 
        print(space + f"Number: {node.v}")
    elif isinstance(node, Var): 
        print(space + f"Variable: {node.n}")
    elif isinstance(node, BinOp):
        print(space + f"Operator: {node.op}")
        print_ast(node.l, level + 1)
        print_ast(node.r, level + 1)
    elif isinstance(node, Assign):
        print(space + f"Assignment: {node.target}")
        print_ast(node.expr, level + 1)


# =====================================================================
# 6. OPTIMIZER (Constant Folding & Identity Reductions)
# =====================================================================
def optimize(node):
    if isinstance(node, (Num, Var)): 
        return node
    if isinstance(node, Assign): 
        return Assign(node.target, optimize(node.expr))
    
    l, r, op = optimize(node.l), optimize(node.r), node.op
    
    # Constant Folding
    if isinstance(l, Num) and isinstance(r, Num):
        if op == '/' and r.v == 0: 
            raise Exception("Optimization Error: Division by zero")
        if op == '+': return Num(l.v + r.v)
        if op == '-': return Num(l.v - r.v)
        if op == '*': return Num(l.v * r.v)
        if op == '/': return Num(l.v // r.v)
        
    # Algebraic Identity Reductions
    if op == '*':
        if (isinstance(l, Num) and l.v == 0) or (isinstance(r, Num) and r.v == 0): 
            return Num(0)
        if isinstance(l, Num) and l.v == 1: return r
        if isinstance(r, Num) and r.v == 1: return l
    if op == '+':
        if isinstance(l, Num) and l.v == 0: return r
        if isinstance(r, Num) and r.v == 0: return l
    if op == '-' and isinstance(r, Num) and r.v == 0: 
        return l
    if op == '/' and isinstance(r, Num) and r.v == 1: 
        return l
        
    return BinOp(l, op, r)


# =====================================================================
# 7. THREE-ADDRESS CODE (TAC) GENERATOR
# =====================================================================
class TACGen:
    def __init__(self): 
        self.t = 0
        self.lines = []

    def emit(self, node):
        if isinstance(node, Num): 
            return str(node.v)
        if isinstance(node, Var): 
            return node.n
        if isinstance(node, BinOp):
            l, r = self.emit(node.l), self.emit(node.r)
            self.t += 1
            temp = f"t{self.t}"
            self.lines.append(f"{temp} = {l} {node.op} {r}")
            return temp
        if isinstance(node, Assign):
            value = self.emit(node.expr)
            self.lines.append(f"{node.target} = {value}")


# =====================================================================
# 8. COMPILER DRIVER
# =====================================================================
def compile_program(src):
    print("=" * 45 + "\nSOURCE CODE: " + src + "\n" + "=" * 45)
    try:
        tokens = tokenize(src)
        print("\n[1. TOKENS]", tokens)
        print("\nToken Classification:")
        for token, category in classify_tokens(tokens): 
            print(f"  {token:10} -> {category}")
        
        ast = Parser(tokens).parse()
        print("\n[2. AST]"); print_ast(ast)
        
        table = {}
        build_symbol_table(ast, table)
        print("\n[3. SYMBOL TABLE]", table)
        semantic_check(ast)
        
        raw = TACGen()
        raw.emit(ast)
        print("\n[4. RAW TAC]")
        for line in raw.lines: 
            print(" ", line)
        
        optimized = optimize(ast)
        print("\n[5. OPTIMIZED AST]"); print_ast(optimized)
        
        opt = TACGen()
        opt.emit(optimized)
        print("\n[6. OPTIMIZED TAC]")
        for line in opt.lines: 
            print(" ", line)
        print(f"\nInstructions reduced: {len(raw.lines)} -> {len(opt.lines)}")
        print("COMPILATION SUCCESSFUL")
    except Exception as e:
        print("\nCOMPILATION FAILED:", e)

if __name__ == "__main__":
    test_input = "x = (3 + 5) * y + 0"
    compile_program(test_input)