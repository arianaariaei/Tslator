import AST
import SymbolTable
from ply.lex import LexToken


class IRGenerator:
    def __init__(self):
        self.code = []
        self.current_register = 1
        self.label_counter = 0
        self.function_registers = {}
        self.current_function = None
        self.loop_stack = []
        self.variable_registers = {}

    def get_next_register(self):
        reg = self.current_register
        self.current_register += 1
        return f"r{reg}"

    def get_next_label(self, prefix="L"):
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def emit(self, op, *args):
        instruction = f"{op} {', '.join(str(arg) for arg in args)}" if args else op
        self.code.append(instruction)

    def emit_label(self, label):
        self.code.append(f"{label}")

    def generate(self, ast, symbol_table):
        self.symbol_table = symbol_table
        if hasattr(ast, 'accept'):
            ast.accept(self)
        return '\n'.join(self.code).rstrip()

    def visit_Program(self, node, symbol_table=None):
        current = node
        while current:
            if hasattr(current, 'func') and current.func:
                current.func.accept(self)
            current = current.prog if hasattr(current, 'prog') else None

    def visit_FunctionDef(self, node, symbol_table=None):
        self.current_function = node.name
        self.current_register = 1
        self.variable_registers = {}

        func_symbol = self.symbol_table.get(node.name)
        if hasattr(func_symbol, 'scope'):
            self.symbol_table = func_symbol.scope
        else:
            raise Exception(f"No scope found for function '{node.name}'")

        self.emit_label(f"proc {node.name}")

        param_registers = {}
        max_param_reg_num = 0
        for i, param in enumerate(node.fmlparams.parameters):
            reg_num = i + 1
            reg = f"r{reg_num}"
            param_registers[param.id] = reg
            self.variable_registers[param.id] = reg
            symbol = self.symbol_table.get(param.id)
            if symbol:
                symbol.set_register(reg)
            max_param_reg_num = max(max_param_reg_num, reg_num)

        self.function_registers[node.name] = param_registers
        self.current_register = max_param_reg_num + 1

        if hasattr(node, 'body') and node.body:
            node.body.accept(self)

        if node.name != "main" and (not self.code or not self.code[-1].strip().endswith('ret')):
            self.emit("mov", "r0", "0")
            self.emit("ret")

    def visit_Body(self, node, symbol_table=None):
        if hasattr(node, 'statement') and node.statement:
            node.statement.accept(self)
        if hasattr(node, 'body') and node.body:
            node.body.accept(self)

    def visit_VariableDecl(self, node, symbol_table=None):
        varname = node.id
        symbol = self.symbol_table.get(varname)
        if not symbol:
            return
        if varname not in self.variable_registers:
            var_reg = self.get_next_register()
            self.variable_registers[varname] = var_reg
            symbol.set_register(var_reg)
        var_reg = self.variable_registers[varname]

        if hasattr(node, 'expr') and node.expr:
            expr_reg = self.visit_expression(node.expr)
            if expr_reg != var_reg:
                self.emit("mov", var_reg, expr_reg)

    def visit_Assignment(self, node, symbol_table=None):
        varname = node.id if isinstance(node.id, str) else node.id.value
        symbol = self.symbol_table.get(varname)
        if not symbol:
            return

        if varname not in self.variable_registers:
            var_reg = self.get_next_register()
            self.variable_registers[varname] = var_reg
            symbol.set_register(var_reg)
        else:
            var_reg = self.variable_registers[varname]

        expr_reg = self.visit_expression(node.expr)
        if expr_reg != var_reg:
            self.emit("mov", var_reg, expr_reg)

    def visit_expression(self, expr):
        if isinstance(expr, LexToken):
            return self.visit_token(expr)
        elif isinstance(expr, AST.BinExpr):
            return self.visit_BinExpr(expr)
        elif isinstance(expr, AST.FunctionCall):
            return self.visit_FunctionCall(expr)
        elif isinstance(expr, AST.OperationOnList):
            return self.visit_OperationOnList(expr)
        elif isinstance(expr, AST.TernaryExpr):
            return self.visit_TernaryExpr(expr)
        elif isinstance(expr, AST.ExprList):
            return self.visit_ExprList(expr)
        else:
            result_reg = self.get_next_register()
            self.emit("mov", result_reg, "0")
            return result_reg

    def visit_token(self, token):
        if token.type == 'NUMBER':
            result_reg = self.get_next_register()
            self.emit("mov", result_reg, token.value)
            return result_reg
        elif token.type == 'STRING':
            result_reg = self.get_next_register()
            self.emit("mov", result_reg, f'"{token.value}"')
            return result_reg
        elif token.type == 'BOOL':
            result_reg = self.get_next_register()
            value = "1" if token.value.lower() == 'true' else "0"
            self.emit("mov", result_reg, value)
            return result_reg
        elif token.type == 'ID':
            varname = token.value
            if varname in self.variable_registers:
                return self.variable_registers[varname]
            elif (self.current_function and
                  self.current_function in self.function_registers and
                  varname in self.function_registers[self.current_function]):
                return self.function_registers[self.current_function][varname]
            else:
                result_reg = self.get_next_register()
                self.emit("mov", result_reg, "0")
                return result_reg
        result_reg = self.get_next_register()
        self.emit("mov", result_reg, "0")
        return result_reg

    def visit_BinExpr(self, node):
        left_reg = self.visit_expression(node.left)
        right_reg = self.visit_expression(node.right)
        result_reg = self.get_next_register()
        if node.op == '+':
            self.emit("add", result_reg, left_reg, right_reg)
        elif node.op == '-':
            self.emit("sub", result_reg, left_reg, right_reg)
        elif node.op == '*':
            self.emit("mul", result_reg, left_reg, right_reg)
        elif node.op == '/':
            self.emit("div", result_reg, left_reg, right_reg)
        elif node.op == '%':
            self.emit("mod", result_reg, left_reg, right_reg)
        elif node.op == '<':
            self.emit("cmp<", result_reg, left_reg, right_reg)
        elif node.op == '>':
            self.emit("cmp>", result_reg, left_reg, right_reg)
        elif node.op == '<=':
            self.emit("cmp<=", result_reg, left_reg, right_reg)
        elif node.op == '>=':
            self.emit("cmp>=", result_reg, left_reg, right_reg)
        elif node.op == '==' or node.op == '=':
            self.emit("cmp=", result_reg, left_reg, right_reg)
        elif node.op == '!=':
            temp_reg = self.get_next_register()
            self.emit("cmp=", temp_reg, left_reg, right_reg)
            self.emit("sub", result_reg, "1", temp_reg)
        elif node.op == '&&':
            self.emit("mul", result_reg, left_reg, right_reg)
        elif node.op == '||':
            temp_reg = self.get_next_register()
            self.emit("add", temp_reg, left_reg, right_reg)
            self.emit("cmp>", result_reg, temp_reg, "0")
        return result_reg

    def visit_FunctionCall(self, node, symbol_table=None):
        if node.id == 'scan':
            result_reg = self.get_next_register()
            self.emit("call", "iget", result_reg)
            return result_reg
        elif node.id == 'print':
            if node.args and hasattr(node.args, 'exprs') and node.args.exprs:
                arg_reg = self.visit_expression(node.args.exprs[0])
                self.emit("call", "iput", arg_reg)
            return None
        else:
            result_reg = self.get_next_register()
            args = []
            if node.args and hasattr(node.args, 'exprs'):
                for arg_expr in node.args.exprs:
                    arg_reg = self.visit_expression(arg_expr)
                    args.append(arg_reg)
            self.emit("call", node.id, result_reg, *args)
            return result_reg

    def visit_OperationOnList(self, node):
        base_reg = self.visit_expression(node.expr)
        index_reg = self.visit_expression(node.index_expr)
        result_reg = self.get_next_register()
        addr_reg = self.get_next_register()
        temp_reg = self.get_next_register()
        self.emit("mul", temp_reg, index_reg, "8")
        self.emit("add", addr_reg, base_reg, temp_reg)
        self.emit("ld", result_reg, addr_reg)
        return result_reg

    def visit_TernaryExpr(self, node):
        cond_reg = self.visit_expression(node.cond)
        result_reg = self.get_next_register()
        false_label = self.get_next_label("FALSE")
        end_label = self.get_next_label("END")
        self.emit("jz", cond_reg, false_label)
        true_reg = self.visit_expression(node.first_expr)
        self.emit("mov", result_reg, true_reg)
        self.emit("jmp", end_label)
        self.emit_label(false_label)
        false_reg = self.visit_expression(node.second_expr)
        self.emit("mov", result_reg, false_reg)
        self.emit_label(end_label)
        return result_reg

    def visit_ExprList(self, node):
        result_reg = self.get_next_register()
        size = len(node.exprs)
        bytes_needed = size * 8
        self.emit("mov", result_reg, bytes_needed)
        self.emit("call", "mem", result_reg)
        for i, expr in enumerate(node.exprs):
            expr_reg = self.visit_expression(expr)
            offset_reg = self.get_next_register()
            addr_reg = self.get_next_register()
            self.emit("mov", offset_reg, str(i * 8))
            self.emit("add", addr_reg, result_reg, offset_reg)
            self.emit("st", expr_reg, addr_reg)
        return result_reg

    def visit_ReturnInstruction(self, node, symbol_table=None):
        if node.expr and isinstance(node.expr, AST.BinExpr):
            left_reg = self.visit_expression(node.expr.left)
            right_reg = self.visit_expression(node.expr.right)
            op = node.expr.op
            if op == '+':
                self.emit("add", "r0", left_reg, right_reg)
            elif op == '-':
                self.emit("sub", "r0", left_reg, right_reg)
            elif op == '*':
                self.emit("mul", "r0", left_reg, right_reg)
            elif op == '/':
                self.emit("div", "r0", left_reg, right_reg)
            elif op == '%':
                self.emit("mod", "r0", left_reg, right_reg)
            else:
                expr_reg = self.visit_expression(node.expr)
                if expr_reg != "r0":
                    self.emit("mov", "r0", expr_reg)
        elif node.expr:
            expr_reg = self.visit_expression(node.expr)
            if expr_reg != "r0":
                self.emit("mov", "r0", expr_reg)
        else:
            self.emit("mov", "r0", "0")
        self.emit("ret")

    def visit_IfOrIfElseInstruction(self, node):
        cond_reg = self.visit_expression(node.cond)
        if node.else_statement:
            else_label = self.get_next_label("ELSE")
            end_label = self.get_next_label("ENDIF")
            self.emit("jz", cond_reg, else_label)
            node.if_statement.accept(self)
            self.emit("jmp", end_label)
            self.emit_label(else_label)
            node.else_statement.accept(self)
            self.emit_label(end_label)
        else:
            end_label = self.get_next_label("ENDIF")
            self.emit("jz", cond_reg, end_label)
            node.if_statement.accept(self)
            self.emit_label(end_label)

    def visit_WhileInstruction(self, node):
        loop_label = self.get_next_label("WHILE")
        end_label = self.get_next_label("ENDWHILE")
        self.loop_stack.append((loop_label, end_label))
        self.emit_label(loop_label)
        cond_reg = self.visit_expression(node.cond)
        self.emit("jz", cond_reg, end_label)
        node.while_statement.accept(self)
        self.emit("jmp", loop_label)
        self.emit_label(end_label)
        self.loop_stack.pop()

    def visit_ForInstruction(self, node, symbol_table=None):
        loop_var_reg = self.get_next_register()
        start_reg = self.visit_expression(node.start_expr)
        end_reg = self.visit_expression(node.end_expr)
        symbol = self.symbol_table.get(node.id)
        if symbol:
            symbol.set_register(loop_var_reg)
        self.emit("mov", loop_var_reg, start_reg)
        loop_label = self.get_next_label("FOR")
        end_label = self.get_next_label("ENDFOR")
        self.loop_stack.append((loop_label, end_label))
        self.emit_label(loop_label)
        cond_reg = self.get_next_register()
        self.emit("cmp>", cond_reg, loop_var_reg, end_reg)
        self.emit("jnz", cond_reg, end_label)
        if hasattr(node.for_statement, 'accept'):
            node.for_statement.accept(self)
        elif isinstance(node.for_statement, list):
            for stmt in node.for_statement:
                if hasattr(stmt, 'accept'):
                    stmt.accept(self)
        self.emit("add", loop_var_reg, loop_var_reg, "1")
        self.emit("jmp", loop_label)
        self.emit_label(end_label)
        self.loop_stack.pop()

    def visit_Block(self, node, symbol_table=None):
        if hasattr(node, 'body') and node.body:
            node.body.accept(self)

    def visit_ContinueInstruction(self, node):
        if self.loop_stack:
            loop_label, _ = self.loop_stack[-1]
            self.emit("jmp", loop_label)

    def visit_BreakInstruction(self, node):
        if self.loop_stack:
            _, end_label = self.loop_stack[-1]
            self.emit("jmp", end_label)
