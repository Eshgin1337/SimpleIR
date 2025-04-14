import sys
from antlr4 import *
from antlr4.tree.Tree import TerminalNodeImpl, ErrorNodeImpl
from antlr4 import ParserRuleContext 

sys.path.append('./')
from grammar.WhileLexer import WhileLexer
from grammar.WhileParser import WhileParser
from grammar.WhileVisitor import WhileVisitor

class Printer(WhileVisitor):
    # --- Visitor class content remains unchanged ---
    # (Includes visitCompound, visitIf, visitWhile, visitDeclarationStmt, etc.
    #  using the inner_ctx pattern and correct formatting/semicolon logic)
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    " # 4 spaces indentation

    # --- Indentation Helpers ---
    def increase_indent(self): self.indent_level += 1
    def decrease_indent(self):
        if self.indent_level > 0: self.indent_level -= 1
    def get_indent(self): return self.indent_str * self.indent_level

    # --- Statement Visitors (Matching Labels on rule 's') ---
    def visitDeclarationStmt(self, ctx: WhileParser.DeclarationStmtContext):
        decl_ctx = ctx.declaration()
        if decl_ctx is None: return "<Error: Missing declaration>"
        type_name = decl_ctx.typeName.text
        var_name = decl_ctx.ID().getText()
        size_ctx = decl_ctx.size
        if size_ctx: # Array declaration
            size = size_ctx.text # Use .text for token
            return f"{self.get_indent()}{type_name} {var_name}[{size}]" # No ;
        else: # Scalar declaration
            return f"{self.get_indent()}{type_name} {var_name}" # No ;

    def visitAssignmentStmt(self, ctx: WhileParser.AssignmentStmtContext):
        assign_ctx = ctx.assignment()
        if assign_ctx is None: return "<Error: Missing assignment>"
        target_ctx = assign_ctx.assignTarget()
        rhs_expr_str = self.visit(assign_ctx.e())
        if isinstance(target_ctx, WhileParser.AssignVarTargetContext):
            lhs_str = target_ctx.ID().getText()
        elif isinstance(target_ctx, WhileParser.AssignArrayTargetContext):
            array_name = target_ctx.ID().getText()
            index_expr_str = self.visit(target_ctx.e())
            lhs_str = f"{array_name}[{index_expr_str}]"
        else:
            lhs_str = "<error_unknown_target>"
        return f"{self.get_indent()}{lhs_str} := {rhs_expr_str}" # No ;

    def visitSkip(self, ctx: WhileParser.SkipContext):
        return f"{self.get_indent()}skip" # No ;

    def visitCompound(self, ctx: WhileParser.CompoundContext):
        inner_ctx = ctx.compound_stmt()
        if inner_ctx is None:
            current_indent = self.get_indent()
            return f"{current_indent}begin\n{current_indent}end"
        current_indent = self.get_indent()
        statements = []
        self.increase_indent()
        if inner_ctx.children:
             for child in inner_ctx.children:
                  expected_stmt_types = (
                      WhileParser.DeclarationStmtContext,
                      WhileParser.AssignmentStmtContext,
                      WhileParser.SkipContext,
                      WhileParser.CompoundContext,
                      WhileParser.IfContext,
                      WhileParser.WhileContext
                  )
                  if isinstance(child, ParserRuleContext) and isinstance(child, expected_stmt_types):
                      stmt_str = self.visit(child)
                      if stmt_str is not None:
                          statements.append(stmt_str)
        self.decrease_indent()
        if not statements:
            return f"{current_indent}begin\n{current_indent}end"
        inner_code = f";\n".join(statements)
        return f"{current_indent}begin\n{inner_code}\n{current_indent}end"

    def visitIf(self, ctx: WhileParser.IfContext):
        inner_ctx = ctx.if_stmt()
        if inner_ctx is None: return "<Error: Missing if_stmt>"
        condition = self.visit(inner_ctx.e())
        current_indent = self.get_indent()
        self.increase_indent()
        then_block_str = self.visit(inner_ctx.s(0))
        self.decrease_indent()
        self.increase_indent()
        else_block_str = self.visit(inner_ctx.s(1))
        self.decrease_indent()
        return (f"{current_indent}if {condition} then\n"
                f"{then_block_str}\n"
                f"{current_indent}else\n"
                f"{else_block_str}")

    def visitWhile(self, ctx: WhileParser.WhileContext):
        inner_ctx = ctx.while_stmt()
        if inner_ctx is None: return "<Error: Missing while_stmt>"
        condition = self.visit(inner_ctx.e())
        current_indent = self.get_indent()
        self.increase_indent()
        body_str = self.visit(inner_ctx.s()) # Use s() - corrected
        self.decrease_indent()
        return (f"{current_indent}while {condition} do\n"
                f"{body_str}")

    # --- Unified Expression Visitors ---
    def visitEBinOpAndOr(self, ctx: WhileParser.EBinOpAndOrContext):
        left = self.visit(ctx.e(0))
        op = ctx.op.text
        right = self.visit(ctx.e(1))
        if isinstance(ctx.e(0), WhileParser.ECompContext): left = f"({left})"
        if isinstance(ctx.e(1), WhileParser.ECompContext): right = f"({right})"
        if op == 'and':
            if isinstance(ctx.e(0), WhileParser.EBinOpAndOrContext) and ctx.e(0).op.text == 'or': left = f"({left})"
            if isinstance(ctx.e(1), WhileParser.EBinOpAndOrContext) and ctx.e(1).op.text == 'or': right = f"({right})"
        return f"{left} {op} {right}"
    def visitEComp(self, ctx: WhileParser.ECompContext): return self.visit(ctx.compExpr())
    def visitEBinOpComp(self, ctx: WhileParser.EBinOpCompContext):
        left = self.visit(ctx.compExpr(0))
        op = ctx.op.text
        right = self.visit(ctx.compExpr(1))
        return f"{left} {op} {right}"
    def visitEAdd(self, ctx: WhileParser.EAddContext): return self.visit(ctx.addExpr())
    def visitEBinOpAddSub(self, ctx: WhileParser.EBinOpAddSubContext):
        left = self.visit(ctx.addExpr(0))
        op = ctx.op.text
        right = self.visit(ctx.addExpr(1))
        if isinstance(ctx.addExpr(0), WhileParser.EMultContext): left = f"({left})"
        if isinstance(ctx.addExpr(1), WhileParser.EMultContext): right = f"({right})"
        return f"{left} {op} {right}"
    def visitEMult(self, ctx: WhileParser.EMultContext): return self.visit(ctx.multExpr())
    def visitEBinOpMulDiv(self, ctx: WhileParser.EBinOpMulDivContext):
        left = self.visit(ctx.multExpr(0))
        op = ctx.op.text
        right = self.visit(ctx.multExpr(1))
        if isinstance(ctx.multExpr(0), WhileParser.EUnaryContext): left = f"({left})"
        if isinstance(ctx.multExpr(1), WhileParser.EUnaryContext): right = f"({right})"
        return f"{left} {op} {right}"
    def visitEUnary(self, ctx: WhileParser.EUnaryContext): return self.visit(ctx.unaryExpr())
    def visitENot(self, ctx: WhileParser.ENotContext):
        operand_ctx = ctx.unaryExpr()
        operand_str = self.visit(operand_ctx)
        if isinstance(operand_ctx, (WhileParser.EBinOpAndOrContext, WhileParser.ECompContext, WhileParser.EAddContext, WhileParser.EMultContext)): return f"not ({operand_str})"
        else: return f"not {operand_str}"
    def visitEPrimary(self, ctx: WhileParser.EPrimaryContext): return self.visit(ctx.primaryExpr())
    # --- Primary Expression Visitors ---
    def visitTrue(self, ctx: WhileParser.TrueContext): return "true"
    def visitFalse(self, ctx: WhileParser.FalseContext): return "false"
    def visitVar(self, ctx: WhileParser.VarContext): return ctx.ID().getText()
    def visitNum(self, ctx: WhileParser.NumContext): return ctx.NUM().getText()
    def visitArrayAccess(self, ctx: WhileParser.ArrayAccessContext):
        array_name = ctx.ID().getText()
        index_expr = self.visit(ctx.e())
        return f"{array_name}[{index_expr}]"
    def visitParen(self, ctx: WhileParser.ParenContext): return f"({self.visit(ctx.e())})"


# --- Main Execution Logic ---
if __name__ == "__main__":
    print("Enter While program code (end with EOF, e.g., Ctrl+D in Linux/macOS, Ctrl+Z Enter in Windows):", file=sys.stderr)
    input_text_original = sys.stdin.read() # Read all input
    input_text_stripped = input_text_original.strip() # Version for checking wrap

    # --- ADDED: Check if input needs wrapping ---
    if not (input_text_stripped.startswith("begin") and input_text_stripped.endswith("end")):
        print("DEBUG: Auto-wrapping input with begin...end", file=sys.stderr)
        # Wrap the stripped text to avoid issues if original had leading/trailing code/comments
        input_text_to_parse = f"begin\n{input_text_stripped}\nend"
    else:
        input_text_to_parse = input_text_original # Parse original if already wrapped

    input_stream = InputStream(input_text_to_parse)
    # --- END ADDED section ---

    lexer = WhileLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = WhileParser(stream)
    parser.removeErrorListeners()

    try:
        tree = parser.s()
    except Exception as e:
        print(f"Error during parsing setup or start rule invocation: {e}\n", file=sys.stderr)
        exit(1)

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors detected during parsing.", file=sys.stderr)
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
    print(formatted_code) # Print the result from the visitor