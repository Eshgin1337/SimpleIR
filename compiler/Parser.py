import sys
from antlr4 import *
sys.path.append('./')

from grammar.WhileLexer import WhileLexer
from grammar.WhileParser import WhileParser
from grammar.WhileVisitor import WhileVisitor

class Printer(WhileVisitor):
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "

    def increase_indent(self):
        self.indent_level += 1

    def decrease_indent(self):
        if self.indent_level > 0:
            self.indent_level -= 1

    def get_indent(self):
        return self.indent_str * self.indent_level

    # --- REVISED: No semicolon here ---
    def visitAssignmentStmt(self, ctx: WhileParser.AssignmentStmtContext):
        assignment_ctx = ctx.assignment()
        if isinstance(assignment_ctx, WhileParser.SimpleAssignmentContext):
            var_name = assignment_ctx.ID().getText()
            expr = self.visit(assignment_ctx.a())
            # Return string WITHOUT trailing semicolon
            return f"{self.get_indent()}{var_name} := {expr}"
        elif isinstance(assignment_ctx, WhileParser.ArrayElementAssignmentContext):
            array_name = assignment_ctx.ID().getText()
            index_expr = self.visit(assignment_ctx.a(0))
            value_expr = self.visit(assignment_ctx.a(1))
            # Return string WITHOUT trailing semicolon
            return f"{self.get_indent()}{array_name}[{index_expr}] := {value_expr}"
        else:
            print(f"Warning: Unrecognized assignment type: {type(assignment_ctx)}", file=sys.stderr)
            return None

    def visitArrayAccess(self, ctx:WhileParser.ArrayAccessContext):
        array_name = ctx.ID().getText()
        index_expr = self.visit(ctx.a())
        return f"{array_name}[{index_expr}]"

    # --- REVISED: No semicolon here ---
    def visitSkip(self, ctx: WhileParser.SkipContext):
        # Return string WITHOUT trailing semicolon
        return f"{self.get_indent()}skip"

    # --- REVISED: Handles joining with semicolons ---
    def visitCompound(self, ctx: WhileParser.CompoundContext):
        if not ctx.s():
            return f"{self.get_indent()}begin\n{self.get_indent()}end" # Empty block

        current_indent = self.get_indent()
        self.increase_indent()
        # Visit children, get statement strings (without semicolons)
        statements = [stmt_str for child in ctx.s() if (stmt_str := self.visit(child)) is not None]
        self.decrease_indent()

        if not statements: # If all children returned None or were filtered
            return f"{current_indent}begin\n{current_indent}end"

        # Join the statements with ";\n" which acts as a separator
        # The last statement will not have ";\n" appended after it.
        inner_code = f";\n".join(statements)

        return f"{current_indent}begin\n{inner_code}\n{current_indent}end"

    # visitIf and visitWhile already produce multi-line structures ending
    # with 'end' or 'done', which don't typically need semicolons after them
    # in block structures. The joining logic in visitCompound will add a
    # semicolon *before* an if/while if needed.

    def visitIf(self, ctx: WhileParser.IfContext):
        condition = self.visit(ctx.b())
        current_indent = self.get_indent()

        self.increase_indent()
        then_block_str = self.visit(ctx.s(0)) if ctx.s(0) else f"{self.get_indent()}skip" # No semicolon here
        self.decrease_indent()

        self.increase_indent()
        else_block_str = self.visit(ctx.s(1)) if ctx.s(1) else f"{self.get_indent()}skip" # No semicolon here
        self.decrease_indent()

        return (f"{current_indent}if {condition} then\n"
                f"{then_block_str}\n"
                f"{current_indent}else\n"
                f"{else_block_str}\n"
                f"{current_indent}end") # 'end' terminates the if structure

    def visitWhile(self, ctx: WhileParser.WhileContext):
        condition = self.visit(ctx.b())
        current_indent = self.get_indent()

        self.increase_indent()
        body_str = self.visit(ctx.s()) if ctx.s() else f"{self.get_indent()}skip" # No semicolon here
        self.decrease_indent()

        return (f"{current_indent}while {condition} do\n"
                f"{body_str}\n"
                f"{current_indent}done") # 'done' terminates the while structure

    # --- Boolean Expression Visitors ---
    def visitNot(self, ctx: WhileParser.NotContext):
        inner_expr = self.visit(ctx.b())
        if isinstance(ctx.b(), (WhileParser.OrContext, WhileParser.AndContext)):
             return f"not ({inner_expr})"
        return f"not {inner_expr}"

    def visitROp(self, ctx: WhileParser.ROpContext):
        left = self.visit(ctx.a(0))
        op = ctx.op.text
        right = self.visit(ctx.a(1))
        return f"{left} {op} {right}"

    def visitOr(self, ctx: WhileParser.OrContext):
        left = self.visit(ctx.b(0))
        right = self.visit(ctx.b(1))
        if isinstance(ctx.b(0), WhileParser.AndContext): left = f"({left})"
        if isinstance(ctx.b(1), WhileParser.AndContext): right = f"({right})"
        return f"{left} or {right}"

    def visitAnd(self, ctx: WhileParser.AndContext):
        left = self.visit(ctx.b(0))
        right = self.visit(ctx.b(1))
        return f"{left} and {right}"

    def visitTrue(self, ctx: WhileParser.TrueContext):
        return "true"

    def visitFalse(self, ctx: WhileParser.FalseContext):
        return "false"

    def visitBParen(self, ctx: WhileParser.BParenContext):
        return f"({self.visit(ctx.b())})"

    # --- Arithmetic Expression Visitors ---
    def visitAOpAddSub(self, ctx:WhileParser.AOpAddSubContext):
        left = self.visit(ctx.a())
        op = ctx.op.text
        right = self.visit(ctx.a_term())
        return f"{left} {op} {right}"

    def visitATerm(self, ctx:WhileParser.ATermContext):
        return self.visit(ctx.a_term())

    def visitAOpMulDiv(self, ctx:WhileParser.AOpMulDivContext):
        left = self.visit(ctx.a_term())
        op = ctx.op.text
        right = self.visit(ctx.a_factor())
        return f"{left} {op} {right}"

    def visitAFactor(self, ctx:WhileParser.AFactorContext):
        return self.visit(ctx.a_factor())

    def visitVar(self, ctx: WhileParser.VarContext):
        return ctx.ID().getText()

    def visitNum(self, ctx: WhileParser.NumContext):
        return ctx.NUM().getText()

    def visitAParen(self, ctx: WhileParser.AParenContext):
        return f"({self.visit(ctx.a())})"

    # Default visitor (fallback)
    def visitChildren(self, node):
        print(f"Warning: Using default visitChildren for node {type(node)}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # --- Main execution logic remains the same ---
    print("Enter While program code (end with EOF, e.g., Ctrl+D in Linux/macOS, Ctrl+Z Enter in Windows):", file=sys.stderr)
    input_stream = InputStream(sys.stdin.read())

    lexer = WhileLexer(input_stream)
    stream = CommonTokenStream(lexer)

    parser = WhileParser(stream)
    parser.removeErrorListeners()

    try:
        tree = parser.s()
    except AttributeError:
        print("Error: Parser object has no attribute 's'. Check your grammar's start rule name.", file=sys.stderr)
        exit(1)
    except Exception as e:
        print(f"An error occurred during parsing: {e}", file=sys.stderr)
        exit(1)

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors detected during parsing. Cannot proceed.", file=sys.stderr)
        exit(1)

    printer = Printer()
    try:
        formatted_code = printer.visit(tree)
        if formatted_code is None:
             print("Warning: Visitor returned None from top level. Check visit methods.", file=sys.stderr)
             formatted_code = ""
    except Exception as e:
        import traceback
        print(f"Error during tree visiting (printing): {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        exit(1)

    print("--- Formatted Code ---")
    print(formatted_code)