import ply.yacc as yacc
import AST
from lexer import tokens, lexer as the_lexer, remove_comments
from SemanticAnalyzer import semanticChecker

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQ', 'NEQ'),
    ('left', 'LESS_THAN', 'GREATER_THAN', 'LTE', 'GTE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULTIPLY', 'DIVIDE'),
    ('right', 'NOT', 'UNARY_PLUS', 'UNARY_MINUS'),
    ('left', 'LSQBR', 'RSQBR'),
)


# Rule 1: prog := func prog | body
def p_prog_func(p):
    """prog : func prog"""
    p[0] = AST.Program(prog=p[2], func=p[1], pos=p.lineno(1))


def p_prog_body(p):
    """prog : body"""
    p[0] = AST.Program(prog=None, func=None, pos=p.lineno(1))


# Rule 2: body := stmt body | empty
def p_body(p):
    """body : stmt body
            | empty"""
    if len(p) == 3:
        p[0] = AST.Body(statement=p[1], body=p[2])
    else:
        p[0] = []


def p_empty(p):
    """empty :"""
    p[0] = []


# Rule 3: func
def p_func_with_body(p):
    """func : FUNK ID LPAREN flist RPAREN LESS_THAN type GREATER_THAN LCURLYEBR body RCURLYEBR"""
    p[0] = AST.FunctionDef(rettype=p[7], name=p[2], params=p[4], body=p[10], pos=p.lineno(1))


def p_func_without_body(p):
    """func : FUNK ID LPAREN flist RPAREN LESS_THAN type GREATER_THAN ARROW RETURN expr SEMI_COLON"""
    return_stmt = AST.ReturnInstruction(expr=p[11], pos=p.lineno(1))
    body = AST.Body(statement=return_stmt, body=[])
    p[0] = AST.FunctionDef(rettype=p[7], name=p[2], params=p[4], body=body, pos=p.lineno(1))


# Rule 4: type
def p_type(p):
    """type : INT
            | VECTOR
            | STR
            | MSTR
            | BOOL
            | NULL"""
    p[0] = p[1]


# Rule 5: stmt
def p_stmt_expr(p):
    """stmt : expr SEMI_COLON"""
    p[0] = p[1]


def p_stmt_defvar(p):
    """stmt : defvar SEMI_COLON"""
    p[0] = p[1]


def p_stmt_func(p):
    """stmt : func SEMI_COLON"""
    p[0] = p[1]


def p_stmt_if(p):
    """stmt : IF LDBLBR expr RDBLBR stmt"""
    p[0] = AST.IfOrIfElseInstruction(cond=p[3], if_statement=p[5], pos=p.lineno(1), else_statement=None)


def p_stmt_if_else(p):
    """stmt : IF LDBLBR expr RDBLBR stmt ELSE stmt"""
    p[0] = AST.IfOrIfElseInstruction(cond=p[3], if_statement=p[5], pos=p.lineno(1), else_statement=p[7])


def p_stmt_while(p):
    """stmt : WHILE LDBLBR expr RDBLBR stmt"""
    p[0] = AST.WhileInstruction(cond=p[3], while_statement=p[5], pos=p.lineno(1))


def p_stmt_do_while(p):
    """stmt : DO stmt WHILE LDBLBR expr RDBLBR"""
    p[0] = AST.DoWhileInstruction(do_statement=p[2], cond=p[5], pos=p.lineno(1))


def p_stmt_for(p):
    """stmt : FOR LPAREN ID EQUAL expr TO expr RPAREN stmt"""
    p[0] = AST.ForInstruction(id=p[3], start_expr=p[5], end_expr=p[7], for_statement=p[9], pos=p.lineno(1))


def p_stmt_begin_end(p):
    """stmt : BEGIN body END"""
    p[0] = AST.Block(body=p[2])


def p_stmt_return(p):
    """stmt : RETURN expr SEMI_COLON"""
    p[0] = AST.ReturnInstruction(expr=p[2], pos=p.lineno(1))


# Rule 6: defvar
def p_defvar_no_init(p):
    """defvar : ID COLON_COLON type"""
    p[0] = AST.VariableDecl(id=p[1], type=p[3], pos=p.lineno(1), expr=None)


def p_defvar_with_init(p):
    """defvar : ID COLON_COLON type EQUAL expr"""
    p[0] = AST.VariableDecl(id=p[1], type=p[3], pos=p.lineno(1), expr=p[5])


# Rule 7: flist
def p_flist_empty(p):
    """flist : empty"""
    p[0] = AST.ParametersList(parameters=[])


def p_flist_single(p):
    """flist : ID AS type"""
    p[0] = AST.ParametersList(parameters=[AST.Parameter(type=p[3], id=p[1])])


def p_flist_multiple(p):
    """flist : ID AS type COMMA flist"""
    p[0] = AST.ParametersList(parameters=[AST.Parameter(type=p[3], id=p[1])] + p[5].parameters)


# Rule 8: clist
def p_clist_empty(p):
    """clist : empty"""
    p[0] = AST.ExprList(exprs=[])


def p_clist_single(p):
    """clist : expr"""
    p[0] = AST.ExprList(exprs=[p[1]])


def p_clist_multiple(p):
    """clist : expr COMMA clist"""
    p[0] = AST.ExprList(exprs=[p[1]] + p[3].exprs)


# Rule 9: expr
def p_expr_array_access(p):
    """expr : expr LSQBR expr RSQBR"""
    p[0] = AST.OperationOnList(expr=p[1], index_expr=p[3], pos=p.lineno(1))


def p_expr_array_literal(p):
    """expr : LSQBR clist RSQBR"""
    p[0] = p[2]


def p_expr_ternary(p):
    """expr : expr QUESTION expr COLON expr"""
    p[0] = AST.TernaryExpr(cond=p[1], first_expr=p[3], second_expr=p[5], pos=p.lineno(1))


def p_expr_binary(p):
    """expr : expr PLUS expr
            | expr MINUS expr
            | expr MULTIPLY expr
            | expr DIVIDE expr
            | expr GREATER_THAN expr
            | expr LESS_THAN expr
            | expr EQ expr
            | expr GTE expr
            | expr LTE expr
            | expr NEQ expr
            | expr OR expr
            | expr AND expr"""
    p[0] = AST.BinExpr(left=p[1], op=p[2], right=p[3], pos=p.lineno(2))


def p_expr_unary(p):
    """expr : NOT expr %prec NOT
            | PLUS expr %prec UNARY_PLUS
            | MINUS expr %prec UNARY_MINUS"""
    p[0] = p[2]


def p_expr_id(p):
    """expr : ID"""
    p[0] = p.slice[1]


def p_expr_assignment(p):
    """expr : ID EQUAL expr"""
    p[0] = AST.Assignment(id=p[1], expr=p[3], pos=p.lineno(1))


def p_expr_array_assignment(p):
    """expr : expr LSQBR expr RSQBR EQUAL expr"""
    array_access = AST.OperationOnList(expr=p[1], index_expr=p[3], pos=p.lineno(1))
    p[0] = AST.Assignment(id=array_access, expr=p[6], pos=p.lineno(1))


def p_expr_function_call(p):
    """expr : ID LPAREN clist RPAREN"""
    p[0] = AST.FunctionCall(id=p[1], args=p[3], pos=p.lineno(1))


def p_expr_number(p):
    """expr : NUMBER"""
    p[0] = p.slice[1]


def p_expr_string(p):
    """expr : STRING"""
    p[0] = p.slice[1]


def p_expr_mstring(p):
    """expr : MSTRING"""
    p[0] = p.slice[1]


def p_expr_paren(p):
    """expr : LPAREN expr RPAREN"""
    p[0] = p[2]


def p_expr_builtin(p):
    """expr : builtin_methods"""
    p[0] = p[1]


def p_builtin_methods(p):
    """builtin_methods : SCAN LPAREN RPAREN
                       | PRINT LPAREN clist RPAREN
                       | LIST LPAREN clist RPAREN
                       | LEN LPAREN clist RPAREN
                       | EXIT LPAREN clist RPAREN"""
    if len(p) == 4:  # SCAN()
        p[0] = AST.FunctionCall(id=p[1], args=AST.ExprList(exprs=[]), pos=p.lineno(1))
    else:
        p[0] = AST.FunctionCall(id=p[1], args=p[3], pos=p.lineno(1))


def p_error(p: yacc.YaccProduction):
    pass


parser = yacc.yacc(start='prog', debug=True)

# Read input
with open("input/sample_code.txt", "r") as file:
    source = file.read()

# Parse
result = parser.parse(source, tracking=True)

# Run semantic analysis
if result:
    checker = semanticChecker()
    checker.analyze(result)
