import SymbolTable
import AST


class semanticChecker:
    def __init__(self):
        self.cast_var = {
            'number': 'int',
            'string': 'str',
            'mstring': 'mstr'
        }
        self.errors = []

    def push_builtins_to_table(self, table):
        builtins = [
            SymbolTable.FunctionSymbol('vector', 'list', AST.ParametersList([AST.Parameter('int', 'size')])),
            SymbolTable.FunctionSymbol('null', 'print', AST.ParametersList([AST.Parameter('str', 'text_to_print')])),
            SymbolTable.FunctionSymbol('int', 'exit', AST.ParametersList([AST.Parameter('int', 'code')])),
            SymbolTable.FunctionSymbol('int', 'length', AST.ParametersList([AST.Parameter('vector', 'vec')])),
            SymbolTable.FunctionSymbol('int', 'scan', AST.ParametersList([])),
        ]
        for b in builtins:
            table.put(b)

    def is_valid_type(self, type_name):
        return type_name in {'int', 'vector', 'str', 'mstr', 'bool', 'null'}

    def check_for_undefined_ids(self, expr, table, lineno):
        from ply.lex import LexToken
        if isinstance(expr, LexToken):
            if expr.type == 'ID':
                var = table.get(expr.value)
                if not var:
                    self.handle_error(lineno,
                                      f"function '{table.function.name if table.function else 'unknown'}': variable '{expr.value}' is not defined.")
                elif isinstance(var, SymbolTable.VariableSymbol) and not var.assigned:
                    self.handle_error(lineno,
                                      f"function '{table.function.name if table.function else 'unknown'}': Variable '{expr.value}' is used before being assigned.")
        elif hasattr(expr, '__dict__'):
            for value in expr.__dict__.values():
                if isinstance(value, (AST.Node, LexToken)):
                    self.check_for_undefined_ids(value, table, lineno)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, (AST.Node, LexToken)):
                            self.check_for_undefined_ids(item, table, lineno)

    def extract_expr_type(self, expr, table):
        from ply.lex import LexToken

        if isinstance(expr, LexToken):
            if expr.type == 'ID':
                var = table.get(expr.value)
                if not var:
                    self.handle_error(expr.lineno,
                                      f"function '{table.function.name if table.function else 'unknown'}': variable '{expr.value}' is not defined.")
                    return 'unknown'
                if isinstance(var, SymbolTable.VariableSymbol) and not var.assigned:
                    self.handle_error(expr.lineno,
                                      f"function '{table.function.name if table.function else 'unknown'}': Variable '{expr.value}' is used before being assigned.")
                if isinstance(var, SymbolTable.VectorSymbol):
                    return 'vector'
                if isinstance(var, SymbolTable.VariableSymbol):
                    return str(var.type).strip()
                return str(var).strip()
            elif expr.type == 'NUMBER':
                return 'int'
            elif expr.type == 'STRING':
                return 'str'
            elif expr.type == 'MSTRING':
                return 'mstr'
            elif expr.type == 'BOOL':
                return 'bool'
            elif expr.type == 'FLOAT':
                self.handle_error(expr.lineno,
                                  f"function '{table.function.name if table.function else 'unknown'}': wrong type 'float' found. types must be one of the following 'int', 'string', 'vector'")
                return 'unknown'
            return self.cast_var.get(expr.type.lower(), 'unknown')

        if isinstance(expr, AST.FunctionCall):
            self.check_for_undefined_ids(expr, table, expr.pos)
            expr.accept(self, table)
            f = table.get(expr.id)
            if f:
                return str(f.rettype).strip()
            return 'unknown'

        if isinstance(expr, AST.ExprList):
            return 'vector'

        if isinstance(expr, AST.Assignment):
            self.check_for_undefined_ids(expr.expr, table, expr.pos)
            expr.accept(self, table)
            return self.extract_expr_type(expr.expr, table)

        if isinstance(expr, AST.TernaryExpr):
            self.check_for_undefined_ids(expr.cond, table, expr.pos)
            self.check_for_undefined_ids(expr.first_expr, table, expr.pos)
            self.check_for_undefined_ids(expr.second_expr, table, expr.pos)
            self.extract_expr_type(expr.cond, table)
            t1 = self.extract_expr_type(expr.first_expr, table)
            t2 = self.extract_expr_type(expr.second_expr, table)
            return t1 if t1 == t2 else 'unknown'

        if isinstance(expr, AST.BinExpr):
            self.check_for_undefined_ids(expr.left, table, expr.pos)
            self.check_for_undefined_ids(expr.right, table, expr.pos)
            left_type = self.extract_expr_type(expr.left, table)
            right_type = self.extract_expr_type(expr.right, table)
            if expr.op in ['+', '-', '*', '/'] and left_type == right_type:
                return left_type
            if expr.op in ['==', '!=', '>', '<', '>=', '<=']:
                return 'bool'
            if expr.op in ['||', '&&']:
                return 'bool'
            return 'unknown'

        if isinstance(expr, AST.OperationOnList):
            self.check_for_undefined_ids(expr.index_expr, table, expr.pos)
            expr.accept(self, table)
            return 'int'

        if hasattr(expr, '__dict__'):
            for value in expr.__dict__.values():
                if isinstance(value, (AST.Node, LexToken)):
                    self.extract_expr_type(value, table)

        return 'unknown'

    def visit_Program(self, node, table):
        if table is None:
            table = SymbolTable.SymbolTable(None, None)
        self.push_builtins_to_table(table)

        current = node
        while current:
            if current.func:
                f = current.func
                func_sym = SymbolTable.FunctionSymbol(f.rettype, f.name, f.fmlparams)
                table.put(func_sym)
            current = current.prog

        self.analyze_function_bodies(node, table)
        return table

    def analyze_function_bodies(self, node, table):
        current = node
        while current:
            if current.func:
                current.func.accept(self, table)
            current = current.prog

    def visit_FunctionDef(self, node, parent_table):
        func_symbol = parent_table.get(node.name)
        table = SymbolTable.SymbolTable(parent_table, func_symbol)
        func_symbol.scope = table
        table.function = func_symbol
        for param in node.fmlparams.parameters:
            if not self.is_valid_type(param.type):
                self.handle_error(node.pos, f"Invalid parameter type '{param.type}'")
            if param.type == 'vector':
                table.put(SymbolTable.VectorSymbol(param.id, 0))
            else:
                table.put(SymbolTable.VariableSymbol(param.type, param.id, True))

        node.body.accept(self, table)

    def visit_Body(self, node, table):
        if node.statement:
            node.statement.accept(self, table)
        if node.body:
            node.body.accept(self, table)

    def visit_VariableDecl(self, node, table):
        if not self.is_valid_type(node.type):
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': wrong type '{node.type}'")
            return
        if node.type == 'vector':
            table.put(SymbolTable.VectorSymbol(node.id, 0))
        else:
            table.put(SymbolTable.VariableSymbol(node.type, node.id, node.expr is not None))
        if node.expr:
            self.check_for_undefined_ids(node.expr, table, node.pos)
            self.extract_expr_type(node.expr, table)

    def visit_Assignment(self, node, table):
        if isinstance(node.id, AST.OperationOnList):
            node.id.accept(self, table)
            return

        varname = node.id.value if hasattr(node.id, 'value') else node.id
        var = table.get(varname)

        if not var:
            self.handle_error(node.pos,
                              f"Variable '{varname}' not defined but used in assignment in function '{table.function.name if table.function else 'unknown'}")
            return

        var.assigned = True

        self.check_for_undefined_ids(node.expr, table, node.pos)
        self.extract_expr_type(node.expr, table)

    def visit_FunctionCall(self, node, table):
        func = table.get(node.id)
        if not isinstance(func, SymbolTable.FunctionSymbol):
            self.handle_error(node.pos,
                              f"'{node.id}' is not a function.")
            return
        if not func:
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': Function '{node.id}' not defined.")
            return

        expected = len(func.params.parameters)
        got = len(node.args.exprs) if node.args else 0

        if func.name == "print":
            printable_types = {"int", "bool", "str", "mstr"}
            if got != expected:
                self.handle_error(node.pos, f"function 'print': expects {expected} arguments but got {got}.")
            else:
                for arg in node.args.exprs:
                    self.check_for_undefined_ids(arg, table, node.pos)
                    arg_type = self.extract_expr_type(arg, table)
                    if arg_type not in printable_types:
                        self.handle_error(node.pos,
                                          f"function 'print': argument must be printable (int, bool, str, mstr), but got '{arg_type}' instead.")
            return

        if expected != got:
            self.handle_error(node.pos, f"function '{func.name}': expects {expected} arguments but got {got}.")
        else:

            for i, arg in enumerate(node.args.exprs):
                param_type = func.params.parameters[i].type
                param_name = func.params.parameters[i].id
                self.check_for_undefined_ids(arg, table, node.pos)
                arg_type = self.extract_expr_type(arg, table)
                if arg_type is None or param_type is None:
                    self.handle_error(node.pos,
                                      f"function '{func.name}': cannot determine type of argument '{param_name}'")
                elif isinstance(arg_type, SymbolTable.VectorSymbol):
                    if param_type != 'vector':
                        self.handle_error(node.pos,
                                          f"function '{func.name}': expected '{param_name}' to be of type '{param_type}', but got 'vector' instead.")

                arg_type_str = str(arg_type).strip()

                param_type_str = str(param_type).strip()
                if arg_type_str != param_type_str:
                    self.handle_error(node.pos,

                                      f"function '{func.name}': expected '{param_name}' to be of type '{param_type_str}', but got '{arg_type_str}' instead.")

    def visit_ReturnInstruction(self, node, table):
        self.check_for_undefined_ids(node.expr, table, node.pos)
        expr_type = self.extract_expr_type(node.expr, table)
        expected = table.function.rettype
        if expr_type != expected:
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': wrong return type. expected '{expected}' but got '{expr_type}'.")

    def visit_IfOrIfElseInstruction(self, node, table):
        self.check_for_undefined_ids(node.cond, table, node.pos)
        cond_type = self.extract_expr_type(node.cond, table)
        if cond_type != 'bool':
            self.handle_error(node.pos, f"If condition must be boolean")
        node.if_statement.accept(self, table)
        if node.else_statement:
            node.else_statement.accept(self, table)

    def visit_WhileInstruction(self, node, table):
        self.check_for_undefined_ids(node.cond, table, node.pos)
        cond_type = self.extract_expr_type(node.cond, table)
        if cond_type != 'bool':
            self.handle_error(node.pos, f"While condition must be boolean")
        node.while_statement.accept(self, table)

    def visit_DoWhileInstruction(self, node, table):
        node.do_statement.accept(self, table)
        self.check_for_undefined_ids(node.cond, table, node.pos)
        cond_type = self.extract_expr_type(node.cond, table)
        if cond_type != 'bool':
            self.handle_error(node.pos, f"Do-while condition must be boolean")

    def visit_ForInstruction(self, node, table):
        self.check_for_undefined_ids(node.start_expr, table, node.pos)
        self.check_for_undefined_ids(node.end_expr, table, node.pos)
        start_type = self.extract_expr_type(node.start_expr, table)
        end_type = self.extract_expr_type(node.end_expr, table)
        if start_type != 'int' or end_type != 'int':
            self.handle_error(node.pos, "Invalid expression type in for loop range. Expected 'int'")

        loop_table = SymbolTable.SymbolTable(table, table.function)
        loop_table.put(SymbolTable.VariableSymbol('int', node.id, True))

        if hasattr(node.for_statement, 'accept'):
            node.for_statement.accept(self, loop_table)
        elif isinstance(node.for_statement, list):
            for stmt in node.for_statement:
                if hasattr(stmt, 'accept'):
                    stmt.accept(self, loop_table)

    def visit_Block(self, node, table):
        node.body.accept(self, table)

    def visit_OperationOnList(self, node, table):
        name = node.expr.value if hasattr(node.expr, 'value') else node.expr
        symbol = table.get(name)
        if not symbol:
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': variable '{name}' is not defined.")
            return
        if not isinstance(symbol, SymbolTable.VectorSymbol):
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': expected '{name}' to be of type 'vector', but got '{symbol.type}' instead.")
        self.check_for_undefined_ids(node.index_expr, table, node.pos)
        idx_type = self.extract_expr_type(node.index_expr, table)
        if idx_type != 'int':
            self.handle_error(node.pos,
                              f"function '{table.function.name if table.function else 'unknown'}': vector index must be 'int'")

    def visit_TernaryExpr(self, node, table):
        self.check_for_undefined_ids(node.cond, table, node.pos)
        self.check_for_undefined_ids(node.first_expr, table, node.pos)
        self.check_for_undefined_ids(node.second_expr, table, node.pos)
        cond_type = self.extract_expr_type(node.cond, table)
        if cond_type != 'bool':
            self.handle_error(node.pos, f"Ternary condition must be boolean")
        self.extract_expr_type(node.first_expr, table)
        self.extract_expr_type(node.second_expr, table)

    def handle_error(self, pos, msg):
        error_msg = f"Semantic error at line {pos}: {msg}"
        if error_msg not in self.errors:
            self.errors.append(error_msg)

    def analyze(self, ast):
        if hasattr(ast, 'accept'):
            symbol_table = self.visit_Program(ast, None)
            return symbol_table

        if not self.errors:
            print("Semantic analysis completed successfully.")
        else:
            for error in self.errors:
                print(error)
        return None