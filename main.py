import sys
from tabulate import tabulate
from lexer import tokenize
import parser
from SemanticAnalyzer import semanticChecker
from IRGenerator import IRGenerator


def process_input(filename):
    try:
        with open(filename, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        sys.exit(1)


def print_tokens(tokens_list):
    if not tokens_list:
        return
    table_data = [[token.lineno, token.column, token.type, token.value] for token in tokens_list]
    headers = ["Line", "Column", "Token", "Value"]
    print("=" * 60)
    print("LEXICAL ANALYSIS - TOKENS")
    print("=" * 60)
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
    print()


def print_ast(ast, indent=0):
    if ast is None:
        return
    spaces = "  " * indent
    class_name = ast.__class__.__name__
    print(f"{spaces}{class_name}", end="")
    if hasattr(ast, 'name'):
        print(f" (name: {ast.name})", end="")
    if hasattr(ast, 'value'):
        print(f" (value: {ast.value})", end="")
    if hasattr(ast, 'op'):
        print(f" (op: {ast.op})", end="")
    if hasattr(ast, 'type_name'):
        print(f" (type: {ast.type_name})", end="")
    if hasattr(ast, 'return_type'):
        print(f" (return_type: {ast.return_type})", end="")
    if hasattr(ast, 'line'):
        print(f" [line: {ast.line}]", end="")
    print()
    for attr in vars(ast).values():
        if isinstance(attr, list):
            for item in attr:
                if hasattr(item, '__dict__'):
                    print_ast(item, indent + 1)
        elif hasattr(attr, '__dict__'):
            print_ast(attr, indent + 1)


def capture_parsing_output(input_text):
    import io
    import contextlib
    syntax_errors = []
    semantic_errors = []
    ast = None
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            ast = parser.parser.parse(input_text, tracking=True)
    except Exception as e:
        syntax_errors.append(f"Parser exception: {str(e)}")
    captured_lines = output_buffer.getvalue().split('\n')
    for line in captured_lines:
        line = line.strip()
        if not line:
            continue
        if 'Syntax error' in line:
            syntax_errors.append(line)
        elif 'Semantic error' in line or 'Type mismatch' in line or 'Type error' in line:
            semantic_errors.append(line)
        elif 'error' in line.lower() and ('line' in line or 'token' in line):
            if 'semantic' in line.lower() or 'type' in line.lower():
                semantic_errors.append(line)
            else:
                syntax_errors.append(line)
    success = ast is not None and len(syntax_errors) == 0 and len(semantic_errors) == 0
    return ast, syntax_errors, semantic_errors, success


def perform_token_level_semantic_analysis(tokens_list):
    defined_vars = set()
    defined_functions = set(['print', 'scan', 'exit', 'length', 'vector', 'list'])
    semantic_errors = []
    try:
        i = 0
        while i < len(tokens_list):
            token = tokens_list[i]
            if token.type in ['INT', 'STR', 'BOOL', 'VECTOR'] and i + 1 < len(tokens_list):
                if tokens_list[i + 1].type == 'ID':
                    defined_vars.add(tokens_list[i + 1].value)
                    i += 2
                    continue
            if token.type == 'FUNK' and i + 1 < len(tokens_list):
                if tokens_list[i + 1].type == 'ID':
                    defined_functions.add(tokens_list[i + 1].value)
                    i += 2
                    continue
            if token.type == 'ID':
                var_name = token.value
                if i + 1 < len(tokens_list) and tokens_list[i + 1].value == '(':
                    if var_name not in defined_functions:
                        semantic_errors.append(
                            f"Semantic error at line {token.lineno}: Function '{var_name}' not defined")
                else:
                    if var_name not in defined_vars and var_name not in defined_functions:
                        semantic_errors.append(
                            f"Semantic error at line {token.lineno}: Variable '{var_name}' not defined")
            i += 1
        return semantic_errors
    except Exception as e:
        return [f"Error in token-level semantic analysis: {e}"]


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "input/sample_code.tes"
    print(f"Compiling: {filename}")
    print("=" * 80)
    lexical_success = False
    syntax_success = False
    semantic_success = False
    ast = None
    tokens_list = []
    try:
        input_text = process_input(filename)
        lexical_success = True
        print(f"✓ Successfully read input file ({len(input_text)} characters)")
    except Exception as e:
        print(f"✗ Failed to read input file: {e}")
        return
    if lexical_success:
        try:
            tokens_list = tokenize(input_text)
            print_tokens(tokens_list)
        except Exception as e:
            print(f"✗ Lexical analysis failed: {e}")
            lexical_success = False
    print("=" * 60)
    print("SYNTAX & SEMANTIC ANALYSIS")
    print("=" * 60)
    syntax_errors = []
    semantic_errors = []
    if lexical_success:
        ast, syntax_errors, semantic_errors, parsing_success = capture_parsing_output(input_text)
        if syntax_errors:
            print("SYNTAX ERRORS:")
            print("-" * 40)
            for error in syntax_errors:
                print(f"  {error}")
            print()
        if semantic_errors:
            print("SEMANTIC ERRORS:")
            print("-" * 40)
            for error in semantic_errors:
                print(f"  {error}")
            print()
        syntax_success = len(syntax_errors) == 0
        semantic_success = len(semantic_errors) == 0 and ast is not None
        if ast:
            checker = semanticChecker()
            checker.analyze(ast)
            semantic_errors = checker.errors
        syntax_success = len(syntax_errors) == 0
        semantic_success = len(semantic_errors) == 0 and ast is not None
        if syntax_success and semantic_success:
            print("✓ Syntax and semantic analysis completed successfully")
            irgen = IRGenerator()
            symbol_table = checker.visit_Program(ast, None)
            ir_code = irgen.generate(ast, symbol_table)
            with open("output.ir", "w") as f:
                f.write(ir_code)
            print("✓ IR code generated and written to 'output.ir'")
        else:
            if not syntax_success:
                print("✗ Syntax analysis completed with errors")
            if not semantic_success:
                print("✗ Semantic analysis completed with errors")
    else:
        print("Skipping syntax and semantic analysis due to lexical errors")
    if ast is None and lexical_success and len(semantic_errors) == 0:
        print("\n" + "-" * 40)
        print("ADDITIONAL SEMANTIC CHECKS:")
        print("-" * 40)
        token_semantic_errors = perform_token_level_semantic_analysis(tokens_list)
        if token_semantic_errors:
            for error in token_semantic_errors:
                print(f"  {error}")
            semantic_errors.extend(token_semantic_errors)
        else:
            print("  No additional semantic errors found at token level")
    print("\n" + "=" * 80)
    print("COMPILATION SUMMARY")
    print("=" * 80)
    total_syntax_errors = len(syntax_errors)
    total_semantic_errors = len(semantic_errors)
    if lexical_success and syntax_success and semantic_success:
        print("✓ Compilation completed successfully!")
    else:
        print("✗ Compilation completed with errors!")
        print(f"  - Lexical Analysis: {'PASSED' if lexical_success else 'FAILED'}")
        print(f"  - Syntax Analysis: {'PASSED' if syntax_success else 'FAILED'}")
        if total_syntax_errors > 0:
            print(f"    ({total_syntax_errors} syntax error{'s' if total_syntax_errors != 1 else ''})")
        print(f"  - Semantic Analysis: {'PASSED' if semantic_success else 'FAILED'}")
        if total_semantic_errors > 0:
            print(f"    ({total_semantic_errors} semantic error{'s' if total_semantic_errors != 1 else ''})")
    print("=" * 80)


if __name__ == "__main__":
    main()
