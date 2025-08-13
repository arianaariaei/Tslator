import ply.lex as lex
import re

reserved = {
    'funk': 'FUNK',
    'return': 'RETURN',
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'to': 'TO',
    'begin': 'BEGIN',
    'end': 'END',
    'int': 'INT',
    'vector': 'VECTOR',
    'str': 'STR',
    'mstr': 'MSTR',
    'bool': 'BOOL',
    'null': 'NULL',
    'length': 'LEN',
    'as': 'AS',
    'do': 'DO',
    'scan': 'SCAN',
    'print': 'PRINT',
    'list': 'LIST',
    'exit': 'EXIT'
}

tokens = (
    'NUMBER', 'PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE', 'LPAREN', 'RPAREN',
    'LCURLYEBR', 'RCURLYEBR',
    'LDBLBR', 'RDBLBR',  # define doubles BEFORE singles
    'LSQBR', 'RSQBR',
    'SEMI_COLON', 'EQUAL', 'ID', 'STRING', 'MSTRING',
    'LESS_THAN', 'GREATER_THAN', 'COLON_COLON', 'COLON', 'QUESTION',
    'COMMA', 'NOT', 'AND', 'OR', 'EQ', 'NEQ', 'LTE', 'GTE', 'ARROW',
    'FUNK', 'RETURN', 'IF', 'ELSE', 'WHILE', 'FOR', 'TO', 'BEGIN', 'END', 'DO',
    'INT', 'VECTOR', 'STR', 'MSTR', 'BOOL', 'NULL', 'LEN', 'AS',
    'SCAN', 'PRINT', 'LIST', 'EXIT',
)


def remove_comments(input_text):
    protected_strings = []
    string_pattern = r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''

    def replace_strings(match):
        protected_strings.append(match.group(0))
        return f"__STRING_PLACEHOLDER_{len(protected_strings) - 1}__"

    text_without_strings = re.sub(string_pattern, replace_strings, input_text)

    result = list(text_without_strings)
    i = 0
    while i < len(result):
        if i + 1 < len(result) and result[i] == '<' and result[i + 1] == '/':
            comment_start = i
            i += 2
            nesting_level = 1
            while i < len(result) and nesting_level > 0:
                if i + 1 < len(result) and result[i] == '<' and result[i + 1] == '/':
                    nesting_level += 1
                    i += 2
                elif i + 1 < len(result) and result[i] == '/' and result[i + 1] == '>':
                    nesting_level -= 1
                    i += 2
                else:
                    i += 1
            if nesting_level == 0:
                for j in range(comment_start, i):
                    if result[j] != '\n':
                        result[j] = ' '
            else:
                i = comment_start + 1
        else:
            i += 1

    result = ''.join(result)

    for idx, s in enumerate(protected_strings):
        result = result.replace(f"__STRING_PLACEHOLDER_{idx}__", s)

    return result


def t_MSTRING(t):
    r'"""[\s\S]*?"""'
    t.lexer.lineno += t.value.count('\n')
    return t


def t_STRING(t):
    r'"([^\n"\\]|\\.)*"|\'([^\n\'\\]|\\.)*\''
    t.lexer.lineno += t.value.count('\n')
    return t


t_PLUS = r'\+'
t_MINUS = r'\-'
t_MULTIPLY = r'\*'
t_DIVIDE = r'\/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LDBLBR = r'\[\['
t_RDBLBR = r'\]\]'
t_LSQBR = r'\['
t_RSQBR = r'\]'
t_LCURLYEBR = r'\{'
t_RCURLYEBR = r'\}'
t_SEMI_COLON = r';'
t_EQUAL = r'='
t_COLON_COLON = r'::'
t_COLON = r':'
t_QUESTION = r'\?'
t_COMMA = r','
t_ARROW = r'=>'

t_EQ = r'=='
t_NEQ = r'!='
t_LTE = r'<='
t_GTE = r'>='
t_LESS_THAN = r'<'
t_GREATER_THAN = r'>'
t_AND = r'\&\&'
t_OR = r'\|\|'
t_NOT = r'!'

t_NUMBER = r'\d+'


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.column = 1


def t_whitespace(t):
    r'[ \t]+'
    t.lexer.column += len(t.value)
    pass


def t_error(t):
    # collect, don't print
    if not t.value:
        t.lexer.errors.append(f"Lexer error: empty token at line {t.lineno}")
        t.lexer.skip(1)
        return
    ch = t.value[0]
    error_patterns = {
        '@': r'@[a-zA-Z_][a-zA-Z_0-9]*',
        '#': r'#[a-zA-Z_][a-zA-Z_0-9]*',
        '$': r'\$[a-zA-Z_][a-zA-Z_0-9]*',
        '%': r'%',
        '~': r'~',
        '^': r'\^',
        '\\': r'\\',
        '""': r'""[^"]',
        "''": r"''[^']",
    }
    if ch in ['"', "'"]:
        if t.value.startswith('"""'):
            match = re.match(r'"""[^"]*', t.value)
            if match:
                t.lexer.errors.append(f"Unclosed multi-line string at line {t.lineno}")
                t.lexer.skip(len(match.group(0)))
                return
        else:
            match = re.match(rf'{re.escape(ch)}[^{re.escape(ch)}\\]*(?:\\.[^{re.escape(ch)}\\]*)*', t.value)
            if match:
                t.lexer.errors.append(f"Unclosed string at line {t.lineno}")
                t.lexer.skip(len(match.group(0)))
                return
    for first_char, pattern in error_patterns.items():
        if t.value.startswith(first_char):
            match = re.match(pattern, t.value)
            if match:
                t.lexer.errors.append(f"Illegal token '{match.group(0)}' at line {t.lineno}")
                t.lexer.skip(len(match.group(0)))
                return
    t.lexer.errors.append(f"Illegal character '{ch}' at line {t.lineno}")
    t.lexer.skip(1)


lexer = lex.lex()
lexer.column = 1
lexer.errors = []  # collect errors here


def reset_lexer_state():
    lexer.lineno = 1
    lexer.column = 1
    lexer.errors.clear()


def find_column(input_text, token):
    last_cr = input_text.rfind('\n', 0, token.lexpos)
    if last_cr < 0:
        column = token.lexpos + 1
    else:
        column = token.lexpos - last_cr
    return column


def tokenize(input_text, *, preprocessed=False):
    text = input_text if preprocessed else remove_comments(input_text)
    reset_lexer_state()
    lexer.input(text)
    tokens_list = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        tok.column = find_column(text, tok)
        lexer.column += len(str(tok.value))
        tokens_list.append(tok)
    return tokens_list, list(lexer.errors)
