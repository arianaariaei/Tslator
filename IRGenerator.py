import AST
import SymbolTable


class RegisterAllocator:
    def __init__(self):
        self.counter = 0

    def new_register(self):
        reg = f"r{self.counter}"
        self.counter += 1
        return reg

    def reset(self):
        self.counter = 0


class IRContext:
    def __init__(self, symbol_table, function_name):
        self.symbol_table = symbol_table
        self.function_name = function_name
        self.code = []
        self.register_map = {}
        self.reg_alloc = RegisterAllocator()
        self.loop_stack = []

    def emit(self, line):
        self.code.append(line)

    def new_register(self):
        return self.reg_alloc.new_register()


class IRGenerator:
    def __init__(self):
        self.output = []
        self.function_contexts = []

    def generate(self, ast, global_table):
        self.visit(ast, global_table)
        return "\n".join(self.output)

    def visit(self, node, table):
        if node is None:
            return None
        if isinstance(node, list):
            for item in node:
                self.visit(item, table)
            return
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, table)

    def generic_visit(self, node, table):
        raise Exception(f"No visit_{node.__class__.__name__} method")

    def visit_LexToken(self, node, ctx):
        if node.type == 'ID':
            reg = ctx.register_map.get(node.value)
            if reg is None:
                raise Exception(f"Undefined variable: {node.value}")
            return reg
        elif node.type == 'NUMBER':
            reg = ctx.new_register()
            ctx.emit(f"mov {reg}, {node.value}")
            return reg
        elif node.type in ('STRING', 'MSTRING'):
            reg = ctx.new_register()
            ctx.emit(f"mov {reg}, \"{node.value}\")")
            return reg
        elif node.type == 'BOOL':
            reg = ctx.new_register()
            val = 1 if node.value == 'true' else 0
            ctx.emit(f"mov {reg}, {val}")
            return reg
        else:
            raise Exception(f"Unsupported LexToken type: {node.type}")

    def visit_Program(self, node, table):
        self.visit(node.func, table)
        self.visit(node.prog, table)

    def visit_FunctionDef(self, node, table):
        func_symbol = table.get(node.name)
        ctx = IRContext(SymbolTable.SymbolTable(table, func_symbol), node.name)
        self.function_contexts.append(ctx)
        ctx.emit(f"proc {node.name}")

        for i, param in enumerate(node.fmlparams.parameters):
            reg = f"r{i}"
            var = SymbolTable.VariableSymbol(param.type, param.id, True)
            var.set_register(reg)
            ctx.symbol_table.put(var)
            ctx.register_map[param.id] = reg

        ctx.reg_alloc.counter = len(node.fmlparams.parameters)

        self.visit(node.body, ctx)

        if node.rettype == 'null':
            ctx.emit("mov r0, 0")
        if not ctx.code or not ctx.code[-1].startswith("ret"):
            ctx.emit("ret")

        self.output.extend(ctx.code)
        self.function_contexts.pop()

    def visit_Body(self, node, ctx):
        self.visit(node.statement, ctx)
        self.visit(node.body, ctx)

    def visit_VariableDecl(self, node, ctx):
        reg = ctx.new_register()
        var = SymbolTable.VariableSymbol(node.type, node.id, node.expr is not None)
        var.set_register(reg)
        ctx.symbol_table.put(var)
        ctx.register_map[node.id] = reg

        if node.expr:
            expr_reg = self.visit(node.expr, ctx)
            ctx.emit(f"mov {reg}, {expr_reg}")

    def visit_Assignment(self, node, ctx):
        if isinstance(node.id, AST.OperationOnList):
            vec_reg = self.visit(node.id.expr, ctx)
            idx_reg = self.visit(node.id.index_expr, ctx)
            val_reg = self.visit(node.expr, ctx)
            ctx.emit(f"add r_tmp, {vec_reg}, {idx_reg}")
            ctx.emit(f"st {val_reg}, r_tmp")
            return

        var_name = node.id.value if hasattr(node.id, 'value') else node.id
        reg = ctx.register_map.get(var_name)
        expr_reg = self.visit(node.expr, ctx)
        ctx.emit(f"mov {reg}, {expr_reg}")

    def visit_Integer(self, node, ctx):
        reg = ctx.new_register()
        ctx.emit(f"mov {reg}, {node.value}")
        return reg

    def visit_BinExpr(self, node, ctx):
        left_reg = self.visit(node.left, ctx)
        right_reg = self.visit(node.right, ctx)
        result_reg = ctx.new_register()
        op_map = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '%': 'mod', '==': 'cmp==', '!=': 'cmp!=', '<': 'cmp<',
                  '>': 'cmp>', '<=': 'cmp<=', '>=': 'cmp>='}
        op = op_map.get(node.op)
        ctx.emit(f"{op} {result_reg}, {left_reg}, {right_reg}")
        return result_reg

    def visit_FunctionCall(self, node, ctx):
        args = [self.visit(arg, ctx) for arg in node.args.exprs] if node.args else []

        if node.id == 'scan':
            reg = ctx.new_register()
            ctx.emit(f"call iget, {reg}")
            return reg
        elif node.id == 'print':
            for arg in args:
                ctx.emit(f"call iput, {arg}")
            return None
        elif node.id == 'exit':
            ctx.emit(f"call halt, {args[0]}")
            return None
        elif node.id == 'length':
            ctx.emit(f"call len, {args[0]}")
            return args[0]
        elif node.id == 'list':
            reg = ctx.new_register()
            ctx.emit(f"call mem, {args[0]}")
            ctx.emit(f"mov {reg}, r0")
            return reg

        for i, arg in enumerate(args):
            target_reg = f"r{i}"
            if arg != target_reg:
                ctx.emit(f"mov {target_reg}, {arg}")

        ctx.emit(f"call {node.id}")
        return "r0"

    def visit_ReturnInstruction(self, node, ctx):
        reg = self.visit(node.expr, ctx)
        ctx.emit(f"mov r0, {reg}")
        ctx.emit("ret")

    def visit_IfOrIfElseInstruction(self, node, ctx):
        cond_reg = self.visit(node.cond, ctx)
        label_else = f"L{ctx.new_register()}"
        label_end = f"L{ctx.new_register()}"

        ctx.emit(f"jz {cond_reg}, {label_else}")
        self.visit(node.if_statement, ctx)
        ctx.emit(f"jmp {label_end}")
        ctx.emit(f"{label_else}:")
        if node.else_statement:
            self.visit(node.else_statement, ctx)
        ctx.emit(f"{label_end}:")

    def visit_WhileInstruction(self, node, ctx):
        label_start = f"L{ctx.new_register()}"
        label_end = f"L{ctx.new_register()}"
        ctx.loop_stack.append((label_start, label_end))

        ctx.emit(f"{label_start}:")
        cond_reg = self.visit(node.cond, ctx)
        ctx.emit(f"jz {cond_reg}, {label_end}")
        self.visit(node.while_statement, ctx)
        ctx.emit(f"jmp {label_start}")
        ctx.emit(f"{label_end}:")

        ctx.loop_stack.pop()

    def visit_ForInstruction(self, node, ctx):
        var = SymbolTable.VariableSymbol('int', node.id, True)
        reg = ctx.new_register()
        var.set_register(reg)
        ctx.symbol_table.put(var)
        ctx.register_map[node.id] = reg

        start = self.visit(node.start_expr, ctx)
        end = self.visit(node.end_expr, ctx)

        ctx.emit(f"mov {reg}, {start}")
        label_start = f"L{ctx.new_register()}"
        label_end = f"L{ctx.new_register()}"
        ctx.loop_stack.append((label_start, label_end))

        ctx.emit(f"{label_start}:")
        cmp_reg = ctx.new_register()
        ctx.emit(f"cmp<= {cmp_reg}, {reg}, {end}")
        ctx.emit(f"jz {cmp_reg}, {label_end}")
        self.visit(node.for_statement, ctx)
        ctx.emit(f"add {reg}, {reg}, 1")
        ctx.emit(f"jmp {label_start}")
        ctx.emit(f"{label_end}:")

        ctx.loop_stack.pop()

    def visit_ContinueInstruction(self, node, ctx):
        if ctx.loop_stack:
            loop_start, _ = ctx.loop_stack[-1]
            ctx.emit(f"jmp {loop_start}")

    def visit_DoWhileInstruction(self, node, ctx):
        label_start = f"L{ctx.new_register()}"
        label_end = f"L{ctx.new_register()}"
        ctx.loop_stack.append((label_start, label_end))

        ctx.emit(f"{label_start}:")
        self.visit(node.do_statement, ctx)
        cond_reg = self.visit(node.cond, ctx)
        ctx.emit(f"jnz {cond_reg}, {label_start}")

        ctx.loop_stack.pop()

    def visit_Block(self, node, ctx):
        self.visit(node.body, ctx)

    def visit_ExprList(self, node, ctx):
        regs = [self.visit(expr, ctx) for expr in node.exprs]
        return regs[0] if regs else None

    def visit_TernaryExpr(self, node, ctx):
        cond_reg = self.visit(node.cond, ctx)
        label_else = f"L{ctx.new_register()}"
        label_end = f"L{ctx.new_register()}"
        result_reg = ctx.new_register()

        ctx.emit(f"jz {cond_reg}, {label_else}")
        true_reg = self.visit(node.first_expr, ctx)
        ctx.emit(f"mov {result_reg}, {true_reg}")
        ctx.emit(f"jmp {label_end}")
        ctx.emit(f"{label_else}:")
        false_reg = self.visit(node.second_expr, ctx)
        ctx.emit(f"mov {result_reg}, {false_reg}")
        ctx.emit(f"{label_end}:")
        return result_reg

    def visit_OperationOnList(self, node, ctx):
        vec_reg = self.visit(node.expr, ctx)
        idx_reg = self.visit(node.index_expr, ctx)
        addr_reg = ctx.new_register()
        result_reg = ctx.new_register()
        ctx.emit(f"add {addr_reg}, {vec_reg}, {idx_reg}")
        ctx.emit(f"ld {result_reg}, {addr_reg}")
        return result_reg
