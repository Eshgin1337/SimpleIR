import sys
from antlr4 import *

# Ensure grammar package relative path is findable if needed
# (Adjust if your execution directory changes)
# sys.path.append('./') # Usually needed if running from parent dir
# sys.path.append('../') # May be needed if running from compiler/compiler?

# Make sure these imports work after regeneration
try:
    from grammar.TypeWhileLexer import TypeWhileLexer
    from grammar.TypeWhileParser import TypeWhileParser
    from grammar.TypeWhileVisitor import TypeWhileVisitor
except ImportError:
    print("Error: Could not import ANTLR generated files.")
    print("Ensure you are in the 'compiler/compiler' directory or adjust sys.path.")
    print("Also ensure 'make' ran successfully in the 'grammar' directory.")
    exit(1)

# --- Helper Functions ---

# Helper function to check if a type is an array type tuple
def is_array_type(type_info):
    return isinstance(type_info, tuple) and len(type_info) == 3 and type_info[0] == 'array'

# Helper function to get array base type
def get_array_base_type(type_info):
    if is_array_type(type_info):
        return type_info[1] # e.g., 'int' or 'bool'
    return None

# Helper function to get array size
def get_array_size(type_info):
    if is_array_type(type_info):
        return type_info[2] # e.g., 10
    return None

# --- Symbol Table (Global) ---
symtab = {}

# --- Type Checker Visitor ---

class TypeChecker(TypeWhileVisitor):
    def __init__(self):
        super().__init__() # Initialize the base visitor
        self.has_error = False

    # Central error reporting method
    def error(self, message, ctx=None):
        line = ctx.start.line if ctx and hasattr(ctx, 'start') else '?'
        col = ctx.start.column if ctx and hasattr(ctx, 'start') else '?'
        print(f"type error (line {line}:{col}): {message}") # Keep error messages
        self.has_error = True
        # Return None to indicate error downstream if type was expected
        return None

    # --- Statement Visitors ---

    def visitDeclaration(self, ctx: TypeWhileParser.DeclarationContext):
        var_name = ctx.ID().getText()
        base_type_name = ctx.typeName.text # 'int' or 'bool'

        if var_name in symtab:
            return self.error(f"redeclaration of variable '{var_name}'", ctx)

        # Check if the size attribute (NUM token) exists
        if hasattr(ctx, 'size') and ctx.size is not None: # Check for array declaration
            try:
                size = int(ctx.size.text)
                if size <= 0:
                    return self.error(f"array size must be positive, got {size}", ctx)
                # Store array type as ('array', base_type, size)
                array_type_tuple = ('array', base_type_name, size)
                symtab[var_name] = array_type_tuple
            except ValueError:
                return self.error(f"invalid array size '{ctx.size.text}'", ctx)
        else: # It's a scalar declaration
            symtab[var_name] = base_type_name


    def visitAssignment(self, ctx: TypeWhileParser.AssignmentContext):
        # Visit the right-hand side expression first to get its type
        value_ctx = ctx.e()
        value_type = self.visit(value_ctx)
        if value_type is None: return # Error already reported in expression

        # Get the context for the *target* of the assignment (LHS)
        target_ctx = ctx.assignTarget()

        # Case 1: Target is a simple variable (AssignVarTargetContext)
        if hasattr(target_ctx, 'AssignVarTargetContext') or isinstance(target_ctx, TypeWhileParser.AssignVarTargetContext):
            var_name = target_ctx.ID().getText()
            if var_name not in symtab:
                return self.error(f"assignment to undeclared variable '{var_name}'", target_ctx)

            var_type_info = symtab[var_name]
            if is_array_type(var_type_info):
                 return self.error(f"cannot assign directly to array variable '{var_name}', use index", target_ctx)

            if var_type_info != value_type:
                return self.error(f"type mismatch: cannot assign type '{value_type}' to variable '{var_name}' of type '{var_type_info}'", ctx)

        # Case 2: Target is an array element (AssignArrayTargetContext)
        elif hasattr(target_ctx, 'AssignArrayTargetContext') or isinstance(target_ctx, TypeWhileParser.AssignArrayTargetContext):
            array_name = target_ctx.ID().getText()

            if array_name not in symtab:
                return self.error(f"assignment to element of undeclared array '{array_name}'", target_ctx)

            array_type_info = symtab[array_name]
            if not is_array_type(array_type_info):
                return self.error(f"variable '{array_name}' is not an array, cannot index", target_ctx)

            index_ctx = target_ctx.e()
            index_type = self.visit(index_ctx)
            if index_type is None: return # Error already reported
            if index_type != "int":
                return self.error(f"array index must be 'int', but got '{index_type}'", index_ctx)

            array_base_type = get_array_base_type(array_type_info)
            if array_base_type != value_type:
                 return self.error(f"type mismatch: cannot assign type '{value_type}' to element of array '{array_name}' with base type '{array_base_type}'", ctx)

        else:
             return self.error("internal error: unknown assignment target type", ctx)

    def visitIf(self, ctx: TypeWhileParser.IfContext):
        condition_ctx = ctx.e()
        condition_type = self.visit(condition_ctx)
        if condition_type is None: return

        if is_array_type(condition_type):
             return self.error("if condition cannot be an array type", condition_ctx)
        if condition_type != "bool":
            return self.error(f"if condition must be 'bool', but got '{condition_type}'", condition_ctx)

        self.visit(ctx.s(0)) # Visit then branch
        self.visit(ctx.s(1)) # Visit else branch

    def visitWhile(self, ctx: TypeWhileParser.WhileContext):
        condition_ctx = ctx.e()
        condition_type = self.visit(condition_ctx)
        if condition_type is None: return

        if is_array_type(condition_type):
             return self.error("while condition cannot be an array type", condition_ctx)
        if condition_type != "bool":
            return self.error(f"while condition must be 'bool', but got '{condition_type}'", condition_ctx)

        self.visit(ctx.s()) # Visit loop body

    def visitCompound(self, ctx: TypeWhileParser.CompoundContext):
        for statement in ctx.s():
            self.visit(statement)

    def visitSkip(self, ctx: TypeWhileParser.SkipContext):
        pass


    # --- Expression Visitors ---

    def visitTrue(self, ctx: TypeWhileParser.TrueContext):
        return "bool"

    def visitFalse(self, ctx: TypeWhileParser.FalseContext):
        return "bool"

    def visitVar(self, ctx: TypeWhileParser.VarContext):
        var_name = ctx.ID().getText()
        if var_name not in symtab:
            return self.error(f"use of undeclared variable '{var_name}'", ctx)
        return symtab[var_name]

    def visitNum(self, ctx: TypeWhileParser.NumContext):
        return "int"

    def visitArrayAccess(self, ctx: TypeWhileParser.ArrayAccessContext):
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

    # Visitors calling the binary operation helper
    def visitEBinOpAddSub(self, ctx:TypeWhileParser.EBinOpAddSubContext):
        return self._check_bin_op(ctx, "int", "int")
    def visitEBinOpMulDiv(self, ctx:TypeWhileParser.EBinOpMulDivContext):
        return self._check_bin_op(ctx, "int", "int")
    def visitEBinOpComp(self, ctx:TypeWhileParser.EBinOpCompContext):
        return self._check_bin_op(ctx, "int", "bool")
    def visitEBinOpAndOr(self, ctx:TypeWhileParser.EBinOpAndOrContext):
        return self._check_bin_op(ctx, "bool", "bool")

    # Common logic helper for binary operations
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

    # Handles 'not' operator
    def visitENot(self, ctx: TypeWhileParser.ENotContext):
        operand_ctx = ctx.unaryExpr()
        operand_type = self.visit(operand_ctx)

        if operand_type is None: return None

        if is_array_type(operand_type):
            return self.error(f"'not' operator cannot be applied to array type", operand_ctx)
        if operand_type != "bool":
            return self.error(f"'not' operator requires 'bool' operand, but got '{operand_type}'", operand_ctx)

        return "bool"

    # Handles parenthesized expressions
    def visitParen(self, ctx: TypeWhileParser.ParenContext):
        return self.visit(ctx.e())

    # Visitor methods for intermediate expression rules
    def visitEComp(self, ctx:TypeWhileParser.ECompContext):
        return self.visit(ctx.compExpr())
    def visitEAdd(self, ctx:TypeWhileParser.EAddContext):
        return self.visit(ctx.addExpr())
    def visitEMult(self, ctx:TypeWhileParser.EMultContext):
        return self.visit(ctx.multExpr())
    def visitEUnary(self, ctx:TypeWhileParser.EUnaryContext):
        return self.visit(ctx.unaryExpr())
    def visitEPrimary(self, ctx:TypeWhileParser.EPrimaryContext):
        return self.visit(ctx.primaryExpr())


# --- Main execution part ---

if __name__ == "__main__":
    # Read from stdin or file argument
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

    # Standard ANTLR pipeline
    lexer = TypeWhileLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = TypeWhileParser(stream)
    tree = parser.s() # Start parsing from the 's' rule

    if parser.getNumberOfSyntaxErrors() > 0:
        # ANTLR already prints syntax errors to stderr
        print("Syntax errors detected. Type checking aborted.")
        exit(1)

    # Perform type checking
    symtab.clear() # Clear symtab for each run
    type_checker = TypeChecker()
    type_checker.visit(tree)

    # Print symbol table contents in the desired format
    for name, type_info in symtab.items():
       print(f"symtab[{name}]: {type_info}")

    # Determine and print exit code
    exit_code = 1 if type_checker.has_error else 0
    print(f"Exit code: {exit_code}")
    exit(exit_code)