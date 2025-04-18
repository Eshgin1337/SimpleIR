import sys
import os
from antlr4 import *

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from grammar.WhileLexer import WhileLexer
    from grammar.WhileParser import WhileParser
    from grammar.WhileVisitor import WhileVisitor
except ImportError:
    try:
        from WhileLexer import WhileLexer
        from WhileParser import WhileParser
        from WhileVisitor import WhileVisitor
    except ImportError as e:
        print("Error: Could not import ANTLR generated files (WhileLexer/Parser/Visitor).", file=sys.stderr)
        print("Ensure these files exist either directly or within a 'grammar' subdirectory", file=sys.stderr)
        print(f"relative to the script's parent directory ({parent_dir}).", file=sys.stderr)
        print("Also ensure ANTLR generation (e.g., 'make' in grammar dir) was successful.", file=sys.stderr)
        print(f"Original error: {e}", file=sys.stderr)
        sys.exit(1)

def is_array_type(type_info):
    return isinstance(type_info, tuple) and len(type_info) == 3 and type_info[0] == 'array'

def get_array_base_type(type_info):
    if is_array_type(type_info):
        return type_info[1]
    return None

def get_array_size(type_info):
    if is_array_type(type_info):
        return type_info[2]
    return None

symtab = {}

class TypeChecker(WhileVisitor):
    def __init__(self):
        super().__init__()
        self.has_error = False

    def error(self, message, ctx=None):
        line = ctx.start.line if ctx and hasattr(ctx, 'start') else '?'
        col = ctx.start.column if ctx and hasattr(ctx, 'start') else '?'
        print(f"type error (line {line}:{col}): {message}")
        self.has_error = True
        return None

    def visitDeclaration(self, ctx: WhileParser.DeclarationContext):
        var_name = ctx.ID().getText()
        base_type_name = ctx.typeName.text

        if var_name in symtab:
            return self.error(f"redeclaration of variable '{var_name}'", ctx)

        if hasattr(ctx, 'size') and ctx.size is not None:
            try:
                size = int(ctx.size.text)
                if size <= 0:
                    return self.error(f"array size must be positive, got {size}", ctx)
                array_type_tuple = ('array', base_type_name, size)
                symtab[var_name] = array_type_tuple
            except ValueError:
                return self.error(f"invalid array size '{ctx.size.text}'", ctx)
        else:
            symtab[var_name] = base_type_name


    def visitAssignment(self, ctx: WhileParser.AssignmentContext):
        value_ctx = ctx.e()
        value_type = self.visit(value_ctx)
        if value_type is None: return

        target_ctx = ctx.assignTarget()

        # Case 1: Target is a simple variable (AssignVarTargetContext)
        if hasattr(target_ctx, 'AssignVarTargetContext') or isinstance(target_ctx, WhileParser.AssignVarTargetContext):
            var_name = target_ctx.ID().getText()
            if var_name not in symtab:
                return self.error(f"assignment to undeclared variable '{var_name}'", target_ctx)

            var_type_info = symtab[var_name]
            if is_array_type(var_type_info):
                 return self.error(f"cannot assign directly to array variable '{var_name}', use index", target_ctx)

            if var_type_info != value_type:
                return self.error(f"type mismatch: cannot assign type '{value_type}' to variable '{var_name}' of type '{var_type_info}'", ctx)

        # Case 2: Target is an array element (AssignArrayTargetContext)
        elif hasattr(target_ctx, 'AssignArrayTargetContext') or isinstance(target_ctx, WhileParser.AssignArrayTargetContext):
            array_name = target_ctx.ID().getText()

            if array_name not in symtab:
                return self.error(f"assignment to element of undeclared array '{array_name}'", target_ctx)

            array_type_info = symtab[array_name]
            if not is_array_type(array_type_info):
                return self.error(f"variable '{array_name}' is not an array, cannot index", target_ctx)

            index_ctx = target_ctx.e()
            index_type = self.visit(index_ctx)
            if index_type is None: return
            if index_type != "int":
                return self.error(f"array index must be 'int', but got '{index_type}'", index_ctx)

            array_base_type = get_array_base_type(array_type_info)
            if array_base_type != value_type:
                 return self.error(f"type mismatch: cannot assign type '{value_type}' to element of array '{array_name}' with base type '{array_base_type}'", ctx)

        else:
             return self.error("internal error: unknown assignment target type", ctx)

    def visitIf(self, ctx: WhileParser.IfContext):
        condition_ctx = ctx.e()
        condition_type = self.visit(condition_ctx)
        if condition_type is None: return

        if is_array_type(condition_type):
             return self.error("if condition cannot be an array type", condition_ctx)
        if condition_type != "bool":
            return self.error(f"if condition must be 'bool', but got '{condition_type}'", condition_ctx)

        self.visit(ctx.s(0))
        self.visit(ctx.s(1))

    def visitWhile(self, ctx: WhileParser.WhileContext):
        condition_ctx = ctx.e()
        condition_type = self.visit(condition_ctx)
        if condition_type is None: return

        if is_array_type(condition_type):
             return self.error("while condition cannot be an array type", condition_ctx)
        if condition_type != "bool":
            return self.error(f"while condition must be 'bool', but got '{condition_type}'", condition_ctx)

        self.visit(ctx.s())

    def visitCompound(self, ctx: WhileParser.CompoundContext):
        for statement in ctx.s():
            self.visit(statement)

    def visitSkip(self, ctx: WhileParser.SkipContext):
        pass


    def visitTrue(self, ctx: WhileParser.TrueContext):
        return "bool"

    def visitFalse(self, ctx: WhileParser.FalseContext):
        return "bool"

    def visitVar(self, ctx: WhileParser.VarContext):
        var_name = ctx.ID().getText()
        if var_name not in symtab:
            return self.error(f"use of undeclared variable '{var_name}'", ctx)
        return symtab[var_name]

    def visitNum(self, ctx: WhileParser.NumContext):
        return "int"

    def visitArrayAccess(self, ctx: WhileParser.ArrayAccessContext):
        array_name = ctx.ID().getText()
        if array_name not in symtab:
            return self.error(f"use of undeclared array '{array_name}'", ctx)

        array_type_info = symtab[array_name]
        if not is_array_type(array_type_info):
             return self.error(f"variable '{array_name}' is not an array, cannot index", ctx)

        index_ctx = ctx.e()
        index_type = self.visit(index_ctx)
        if index_type is None: return
        if index_type != "int":
            return self.error(f"array index must be 'int', but got '{index_type}'", index_ctx)

        return get_array_base_type(array_type_info)

    def visitEBinOpAddSub(self, ctx: WhileParser.EBinOpAddSubContext):
        return self._check_bin_op(ctx, "int", "int")
    def visitEBinOpMulDiv(self, ctx: WhileParser.EBinOpMulDivContext):
        return self._check_bin_op(ctx, "int", "int")
    def visitEBinOpComp(self, ctx: WhileParser.EBinOpCompContext):
        return self._check_bin_op(ctx, "int", "bool")
    def visitEBinOpAndOr(self, ctx: WhileParser.EBinOpAndOrContext):
        return self._check_bin_op(ctx, "bool", "bool")

    def _check_bin_op(self, ctx, expected_operand_type, result_type):
        left_operand_ctx = ctx.getChild(0)
        right_operand_ctx = ctx.getChild(2)
        op_node = ctx.getChild(1)

        left_type = self.visit(left_operand_ctx)
        right_type = self.visit(right_operand_ctx)
        op = op_node.getText()

        if left_type is None or right_type is None:
            return None

        if is_array_type(left_type):
            return self.error(f"operator '{op}' cannot be applied to array type", left_operand_ctx)
        if is_array_type(right_type):
            return self.error(f"operator '{op}' cannot be applied to array type", right_operand_ctx)

        if left_type != expected_operand_type or right_type != expected_operand_type:
            return self.error(f"operator '{op}' requires operands of type '{expected_operand_type}', but got '{left_type}' and '{right_type}'", ctx)

        return result_type

    def visitENot(self, ctx: WhileParser.ENotContext):
        operand_ctx = ctx.unaryExpr()
        operand_type = self.visit(operand_ctx)

        if operand_type is None: return None

        if is_array_type(operand_type):
            return self.error(f"'not' operator cannot be applied to array type", operand_ctx)
        if operand_type != "bool":
            return self.error(f"'not' operator requires 'bool' operand, but got '{operand_type}'", operand_ctx)

        return "bool"

    def visitParen(self, ctx: WhileParser.ParenContext):
        return self.visit(ctx.e())

    def visitEComp(self, ctx: WhileParser.ECompContext):
        return self.visit(ctx.compExpr())
    def visitEAdd(self, ctx: WhileParser.EAddContext):
        return self.visit(ctx.addExpr())
    def visitEMult(self, ctx: WhileParser.EMultContext):
        return self.visit(ctx.multExpr())
    def visitEUnary(self, ctx: WhileParser.EUnaryContext):
        return self.visit(ctx.unaryExpr())
    def visitEPrimary(self, ctx: WhileParser.EPrimaryContext):
        return self.visit(ctx.primaryExpr())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
        try:
            input_stream = FileStream(input_filename, encoding='utf-8')
        except FileNotFoundError:
            print(f"Error: File not found: {input_filename}")
            exit(1)
        except Exception as e:
             print(f"Error opening file: {e}")
             exit(1)
    else:
        input_text = sys.stdin.read().strip()
        input_stream = InputStream(input_text)

    lexer = WhileLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = WhileParser(stream)
    tree = parser.s()

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors detected. Type checking aborted.")
        exit(1)

    symtab.clear()
    type_checker = TypeChecker()
    type_checker.visit(tree)

    for name, type_info in symtab.items():
       print(f"symtab[{name}]: {type_info}")

    exit_code = 1 if type_checker.has_error else 0
    print(f"Exit code: {exit_code}")
    exit(exit_code)