import sys
from tabulate import tabulate  # optional
from lexer import lexer as LEXER, tokenize, remove_comments, reset_lexer_state
import parser
from SemanticAnalyzer import semanticChecker
from IRGenerator import IRGenerator
from fpdf import FPDF
import io
import contextlib
from fpdf.enums import XPos, YPos

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", "fonts/DejaVuSansMono.ttf")
        self.set_font("DejaVu", "", 10)

    def header(self):
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, "TSLANG Compilation Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)

    def section_title(self, title):
        self.set_font("DejaVu", "", 12)
        self.set_text_color(30, 30, 120)
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)

    def add_code_block(self, code):
        self.set_font("DejaVu", "", 10)
        self.multi_cell(0, 6, code)
        self.ln(2)

    def add_table(self, headers, rows):
        self.set_font("DejaVu", "", 9)
        col_widths = [25] * len(headers)
        for i, header in enumerate(headers):
            self.set_fill_color(220, 220, 220)
            self.cell(col_widths[i], 8, header, border=1, align="C", fill=True)
        self.ln()
        for row in rows:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 6, str(item), border=1)
            self.ln()
        self.ln(3)

def capture_parsing_output(processed_text):
    syntax_errors = []
    semantic_errors = []
    ast = None
    output_buffer = io.StringIO()

    reset_lexer_state()
    try:
        with contextlib.redirect_stdout(output_buffer):
            ast = parser.parser.parse(processed_text, lexer=LEXER, tracking=True)
    except Exception as e:
        syntax_errors.append(f"Parser exception: {str(e)}")

    captured = output_buffer.getvalue().split('\n')
    for line in captured:
        line = line.strip()
        if not line:
            continue
        if 'Syntax error' in line:
            syntax_errors.append(line)
        elif 'Semantic error' in line or 'Type mismatch' in line:
            semantic_errors.append(line)

    success = ast is not None
    return ast, syntax_errors, semantic_errors, success

def generate_ir_code(ast, symbol_table):
    ir_instructions = []
    ir_errors = []
    try:
        if ast:
            ir_generator = IRGenerator()
            ir_generator.symbol_table = symbol_table
            ir_instructions = ir_generator.generate(ast, symbol_table)
        else:
            ir_errors.append("Cannot generate IR: AST is None")
    except Exception as e:
        ir_errors.append(f"IR Generation exception: {str(e)}")
    return ir_instructions, ir_errors

def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "input/sample_code.txt"

    try:
        with open(filename, 'r') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    processed = remove_comments(source_code)

    pdf = PDFReport()
    pdf.add_page()
    pdf.section_title("Source Code")
    pdf.add_code_block(source_code)

    # ---- Lexical Analysis ----
    try:
        tokens_list, lex_errors = tokenize(processed, preprocessed=True)
    except Exception as e:
        lex_errors = [f"Lexical analysis exception: {e}"]
        tokens_list = []

    pdf.section_title("Lexical Analysis - Tokens")
    token_data = [[t.lineno, t.column, t.type, t.value] for t in tokens_list]
    if token_data:
        pdf.add_table(["Line", "Column", "Token", "Value"], token_data)
    else:
        pdf.add_code_block("(no tokens)")

    if lex_errors:
        pdf.section_title("Lexical Errors")
        for err in lex_errors:
            pdf.add_code_block(err)

        # ---- Summary (fail-fast) ----
        print("Syntax Analysis: FAILED (skipped due to lexical errors)")
        print("Semantic Analysis: FAILED (skipped due to lexical errors)")
        print("IR Generation: FAILED (skipped due to lexical errors)")

        pdf.section_title("Compilation Summary")
        summary = [
            f"File: {filename}",
            "Lexical Analysis: FAILED",
            "Syntax Analysis: FAILED",
            "Semantic Analysis: FAILED",
            "IR Generation: FAILED",
        ]
        for line in summary:
            pdf.add_code_block(line)

        try:
            pdf.output("report.pdf")
            print("✓ Compilation report saved to report.pdf")
        except Exception as e:
            print(f"Error saving PDF: {e}")
        return  # STOP PIPELINE HERE


    # ---- Parsing ----
    pdf.section_title("Syntax and Semantic Analysis")
    ast, syntax_errors, semantic_errors, parse_ok = capture_parsing_output(processed)

    if syntax_errors:
        pdf.section_title("Syntax Errors")
        for err in syntax_errors:
            pdf.add_code_block(err)


    # ---- Semantic Analysis ----
    symbol_table = None
    if ast:
        try:
            checker = semanticChecker()
            symbol_table = checker.analyze(ast)
            if checker.errors:
                semantic_errors.extend(checker.errors)
        except Exception as e:
            semantic_errors.append(f"Semantic analysis exception: {e}")

    if semantic_errors:
        pdf.section_title("Semantic Errors")
        for err in semantic_errors:
            pdf.add_code_block(err)


    # ---- IR Generation ----
    pdf.section_title("Intermediate Representation (IR) Generation")
    ir_instructions = []
    ir_errors = []

    if ast and not semantic_errors and not syntax_errors:
        try:
            ir_instructions, ir_errors = generate_ir_code(ast, symbol_table)
            if ir_instructions:
                pdf.section_title("Generated IR Code (Machine Code)")
                if isinstance(ir_instructions, str):
                    instruction_lines = [line.strip() for line in ir_instructions.strip().split('\n') if line.strip()]
                else:
                    instruction_lines = ir_instructions
                ir_code_text = ""
                for instruction in instruction_lines:
                    ir_code_text += instruction + "\n"
                pdf.add_code_block(ir_code_text)
        except Exception as e:
            ir_errors.append(f"IR Generation failed: {str(e)}")
    else:
        ir_errors.append("IR skipped due to earlier errors")

    if ir_errors:
        pdf.section_title("IR Generation Errors")
        for err in ir_errors:
            pdf.add_code_block(err)

    # ---- Summary ----
    pdf.section_title("Compilation Summary")
    summary = [
        f"File: {filename}",
        f"Lexical Analysis: PASSED",
        f"Syntax Analysis: {'PASSED' if not syntax_errors else 'FAILED'}",
        f"Semantic Analysis: {'PASSED' if not semantic_errors else 'FAILED'}",
        f"IR Generation: {'PASSED' if not ir_errors else 'FAILED'}",
    ]
    for line in summary:
        pdf.add_code_block(line)
        print(line)

    try:
        pdf.output("report.pdf")
        print("✓ Compilation report saved to report.pdf")
    except Exception as e:
        print(f"Error saving PDF: {e}")

if __name__ == "__main__":
    main()
