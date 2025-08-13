import sys
from tabulate import tabulate
from lexer import tokenize
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
        self.cell(0, 10, "TESLANG Compilation Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
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


def capture_parsing_output(input_text):
    syntax_errors = []
    semantic_errors = []
    ast = None
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            ast = parser.parser.parse(input_text, tracking=True)
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
    """Generate IR code from AST and symbol table"""
    ir_instructions = []
    ir_errors = []

    try:
        if ast:
            ir_generator = IRGenerator()
            # Pass symbol_table to generator first, then generate from AST
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

    pdf = PDFReport()
    pdf.add_page()
    pdf.section_title("Source Code")
    pdf.add_code_block(source_code)

    # Lexical Analysis
    tokens = []
    try:
        tokens = tokenize(source_code)
    except Exception as e:
        pdf.section_title("Lexical Analysis - Failed")
        pdf.add_code_block(str(e))
        pdf.output("report.pdf")
        return

    # Add token table
    pdf.section_title("Lexical Analysis - Tokens")
    token_data = [[t.lineno, t.column, t.type, t.value] for t in tokens]
    pdf.add_table(["Line", "Column", "Token", "Value"], token_data)

    # Parsing
    pdf.section_title("Syntax and Semantic Analysis")
    ast, syntax_errors, semantic_errors, parse_ok = capture_parsing_output(source_code)

    if syntax_errors:
        pdf.section_title("Syntax Errors")
        for err in syntax_errors:
            pdf.add_code_block(err)

    # Semantic Analysis
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

    # IR Generation - Generate even if there were semantic errors
    pdf.section_title("Intermediate Representation (IR) Generation")
    ir_instructions = []
    ir_errors = []

    if ast:
        try:
            ir_instructions, ir_errors = generate_ir_code(ast, symbol_table)

            if ir_instructions:
                pdf.section_title("Generated IR Code (Machine Code)")

                # Handle if ir_instructions is a string (split by lines)
                if isinstance(ir_instructions, str):
                    instruction_lines = ir_instructions.strip().split('\n')
                    instruction_lines = [line.strip() for line in instruction_lines if line.strip()]
                else:
                    instruction_lines = ir_instructions

                ir_code_text = ""
                for instruction in instruction_lines:
                    ir_code_text += instruction + "\n"
                pdf.add_code_block(ir_code_text)
            else:
                pdf.section_title("IR Generation - No Instructions Generated")
                pdf.add_code_block("No IR instructions were generated")

        except Exception as e:
            ir_errors.append(f"IR Generation failed: {str(e)}")
    else:
        ir_errors.append("Cannot generate IR: AST parsing failed")

    # Display IR errors if any
    if ir_errors:
        pdf.section_title("IR Generation Errors")
        for err in ir_errors:
            pdf.add_code_block(err)
            print(f"IR Error: {err}")

    # Summary
    pdf.section_title("Compilation Summary")
    summary = [
        f"File: {filename}",
        f"Lexical Analysis: {'PASSED' if tokens else 'FAILED'}",
        f"Syntax Analysis: {'PASSED' if not syntax_errors else 'FAILED'}",
        f"Semantic Analysis: {'PASSED' if not semantic_errors else 'FAILED'}",
        f"IR Generation: {'PASSED' if ir_instructions and not ir_errors else 'FAILED'}",
    ]

    for line in summary:
        pdf.add_code_block(line)
        print(line)

    # Save PDF report
    try:
        pdf.output("report.pdf")
        print("✓ Compilation report saved to report.pdf")
    except Exception as e:
        print(f"Error saving PDF: {e}")


if __name__ == "__main__":
    main()