import math
import operator as op


Symbol = str              # A Scheme Symbol is a Python str
Number = (int, float)     # A Scheme Number is a Python int or float
List   = list             # A Scheme List is a Python list


class Env(dict):
    """an environment is a dict of {"var": value} pairs, with an outer Env."""
    def __init__(self, params=(), args=(), outer=None):
        self.update(zip(params, args))
        self.outer = outer

    def find(self, var):
        """find innermost Env where var appears."""
        return self if (var in self) else self.outer.find(var)

class Procedure(object):
    """A user-defined Scheme procedure."""
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        return evaluate(self.body, Env(self.params, args, self.env))

def standard_env():
    """environment with some Scheme standard procedures."""
    env = Env()
    env.update(vars(math)) # sin, cos, sqrt, pi
    env.update({
        "+": op.add,
        "-": op.sub,
        "*": op.mul,
        "/": op.truediv,
        ">": op.gt,
        "<": op.lt,
        "=": op.eq,
        ">=": op.ge,
        "<=": op.le,
        "abs": abs,
        "car": lambda x: x[0],
        "cdr": lambda x: x[1:],
        "eq?": op.is_,
        "map": map,
        "max": max,
        "min": min,
        "not": op.not_,
        "expt": pow,
        "cons": lambda x, y: [x] + y,
        "list": lambda *x: List(x),
        "list?": lambda x: isinstance(x, List),
        "null?": lambda x: x == [],
        "apply": lambda proc, args: proc(*args),
        "begin": lambda *x: x[-1],
        "print": print,
        "round": round,
        "append": op.add,
        "equal?": op.eq,
        "length": len,
        "number?": lambda x: isinstance(x, Number),
        "symbol?": lambda x: isinstance(x, Symbol),
        "procedure?": callable,
    })
    return env

global_env = standard_env()

def tokenize(chars):
    """convert a string of characters into a list of tokens.

    example of input: (+ 2 3)
    example of output: [(, +, 2, 3, )]
    """
    return chars.replace("(", " ( ").replace(")", " ) ").split()

def tokens_to_syntax_tree(tokens):
    """transform a list of tokens into a syntax tree.

    example of input: [(, *, (, +, 2, 3, ), (, +, 3, 4, ), )]
    example of output: [*, [+, 2, 3], [+, 3, 4]]
    """
    if len(tokens) == 0:
        raise SyntaxError("unexpected EOF")
    token = tokens.pop(0)
    if token == "(":
        L = []
        while tokens[0] != ")":
            L.append(tokens_to_syntax_tree(tokens))
        tokens.pop(0) # pop ")"
        return L
    elif token == ")":
        raise SyntaxError("unexpected )")
    else:
        return atom(token)

def atom(token):
    """extract the value of atoms. numbers are numbers, the rest is a symbol."""
    try:
        return int(token)
    except:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)

def parse(program):
    """read a Scheme expression given as a string."""
    return tokens_to_syntax_tree(tokenize(program))

def evaluate(x, env=global_env):
    """evaluate an expression in an environment.

    the evaluator follows the rules:
    ----------------------------------------------------------------------------
    | expression  | syntax      | semantics and example                        |
    ----------------------------------------------------------------------------
    | variable    |             | a symbol is interpreted as a variable name;  |
    | reference   | Symbol      | its value is the variables' value. exm:      |
    |             |             | r => 10 if r was previously defined to be 10 |
    ----------------------------------------------------------------------------
    | constant    | Number      | a number evaluates to itself.                |
    | literal     |             | exs: 12 => 12, -3.45e+6 => -3.45e+6          |
    ----------------------------------------------------------------------------
    |             | (if test    | evaluate test; if true, evaluate and return  |
    | conditional |     conseq  | conseq; else, return alt. ex:                |
    |             |     alt     | (if (> 10 20) (+ 1 1) (+ 3 3)) => 6          |
    ----------------------------------------------------------------------------
    |             |                     | define a new variable and give it    |
    | definition  | (define symbol exp) | the value of evaluating the          |
    |             |                     | expression exp. ex: (define r 10)    |
    ----------------------------------------------------------------------------
    |             |             | if proc is not one of the symbols "if",      |
    | procedure   |             | "define" or "quote", then it's treated as a  |
    | call        | (proc args) | procedure. evaluate proc and all args, and   |
    |             |             | then procedure is applied to the list of arg |
    |             |             | values. ex: (sqrt (* 2 8)) => 4.0            |
    ----------------------------------------------------------------------------
    | quotation   | (quote exp) | return the exp as it is. do not evaluate it. |
    |             |             | ex: (quote (+ 1 2)) => (+ 1 2)               |
    ----------------------------------------------------------------------------
    |             |                   | evaluate exp and assign the value to   |
    | assignment  | (set! symbol exp) | symbol, which must've been previously  |
    |             |                   | defined. ex: (set! r2 (* r r))         |
    ----------------------------------------------------------------------------
    |             | (lambda (symbols) | create a procedure with parameter(s)   |
    | procedure   |  exp)             | named symbols and exp as the body.     |
    |             |                   | ex: (lambda (r) (* pi (* r r)))        |
    ----------------------------------------------------------------------------
    """
    while True:
        if isinstance(x, Symbol):
            return env.find(x)[x]
        elif not isinstance(x, List):
            return x
        elif x[0] == "if":
            _, test, conseq, alt = x
            x = conseq if evaluate(test, env) else alt
        elif x[0] == "define": # defining
            _, symbol, exp = x
            env[symbol] = evaluate(exp, env)
            return None
        elif x[0] == "quote":
            return x[1:]
        elif x[0] == "set!": # assigning
            _, symbol, exp = x
            env.find(symbol)[symbol] = evaluate(exp, env)
            return None
        elif x[0] == "lambda":
            _, params, body = x
            return Procedure(params, body, env)
        else:
            args = [evaluate(arg, env) for arg in x]
            proc = args.pop(0)
            if isinstance(proc, Procedure):
                x = proc.body
                env = Env(proc.params, args, proc.env)
            else:
                return proc(*args)

def schemestr(exp):
    "convert a Python object back into a Scheme-readable string."
    if isinstance(exp, List):
        return "(" + " ".join(map(schemestr, exp)) + ")"
    else:
        return str(exp)

def repl(prompt="schem.py> "):
    "a prompt in the format read-eval-print-loop (repl)."
    while True:
        val = evaluate(parse(input(prompt)))
        if val is not None:
            print(schemestr(val))

if __name__ == "__main__":
    repl()
