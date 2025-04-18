# Interpreter.py - Added input wrapping in main

import sys
from antlr4 import *
sys.path.append('./') # Ensure Python can find grammar files
# Import from code generated by COMBINED grammar
from grammar.WhileLexer import WhileLexer
from grammar.WhileParser import WhileParser
from grammar.WhileVisitor import WhileVisitor

# --- Symbol Table ---
symtab = {}
# --- Runtime Error Helper ---
def runtime_error(msg):
    sys.stderr.write(f"Runtime Error: {msg}\n")
    sys.exit(1)
# --- Type Helper ---
def get_value_type(value):
    if isinstance(value, bool): return 'bool'
    if isinstance(value, int): return 'int'
    return 'unknown'
# --- Default Values for Initialization / Reading ---
DEFAULT_VALUES = {'int': 0, 'bool': False}

# --- Interpreter Class ---
class Interpreter(WhileVisitor):
    # --- Visitor class content remains unchanged ---
    # (Includes visitCompound, visitIf, visitWhile with inner_ctx fixes,
    #  visitDeclarationStmt, visitAssignmentStmt, expression visitors, etc.)
    def visitDeclarationStmt(self, ctx: WhileParser.DeclarationStmtContext):
        decl_ctx = ctx.declaration()
        if decl_ctx is None: runtime_error("Internal: Missing declaration context.")
        var_name = decl_ctx.ID().getText()
        type_name = decl_ctx.typeName.text
        if var_name in symtab: runtime_error(f"Variable '{var_name}' already declared.")
        size_ctx = decl_ctx.size
        if size_ctx:
            try:
                size = int(size_ctx.text) # Use .text
                if size <= 0: runtime_error(f"Array size must be positive for '{var_name}'.")
            except ValueError: runtime_error(f"Invalid array size '{size_ctx.text}' for '{var_name}'.")
            symtab[var_name] = {'type': 'array', 'value': {}, 'size': size, 'element_type': type_name }
        else:
             symtab[var_name] = {'type': type_name, 'value': DEFAULT_VALUES[type_name], 'size': None, 'element_type': None }
        return None
    def visitAssignmentStmt(self, ctx: WhileParser.AssignmentStmtContext):
        assignment_ctx = ctx.assignment()
        if assignment_ctx is None: runtime_error("Internal: Missing assignment context.")
        target_ctx = assignment_ctx.assignTarget()
        rhs_value = self.visit(assignment_ctx.e())
        rhs_type = get_value_type(rhs_value)
        if isinstance(target_ctx, WhileParser.AssignVarTargetContext):
            var_name = target_ctx.ID().getText()
            if var_name not in symtab: runtime_error(f"Variable '{var_name}' not declared.")
            var_info = symtab[var_name]
            expected_type = var_info['type']
            if expected_type == 'array': runtime_error(f"Type Error: Cannot assign scalar value to array variable '{var_name}'.")
            if expected_type != rhs_type: runtime_error(f"Type Error: Cannot assign value of type '{rhs_type}' to variable '{var_name}' of declared type '{expected_type}'.")
            var_info['value'] = rhs_value
            return rhs_value
        elif isinstance(target_ctx, WhileParser.AssignArrayTargetContext):
            array_name = target_ctx.ID().getText()
            if array_name not in symtab: runtime_error(f"Array variable '{array_name}' not declared.")
            array_info = symtab[array_name]
            if array_info['type'] != 'array': runtime_error(f"Type Error: Variable '{array_name}' is not an array.")
            expected_element_type = array_info['element_type']
            array_size = array_info['size']
            index_value = self.visit(target_ctx.e())
            if not isinstance(index_value, int): runtime_error(f"Array index for '{array_name}' must be an integer, got {type(index_value)}.")
            if not (0 <= index_value < array_size): runtime_error(f"Array index out of bounds for '{array_name}': index={index_value}, size={array_size}.")
            if expected_element_type != rhs_type: runtime_error(f"Type Error: Cannot assign value of type '{rhs_type}' to element of array '{array_name}' expecting element type '{expected_element_type}'.")
            array_info['value'][index_value] = rhs_value
            return rhs_value
        else:
            runtime_error("Internal error: Unknown assignment target context type.")
            return None
    def visitSkip(self, ctx: WhileParser.SkipContext): return None
    def visitCompound(self, ctx: WhileParser.CompoundContext):
        inner_ctx = ctx.compound_stmt();
        if inner_ctx is None: return None
        num_statements = 0
        if hasattr(inner_ctx, 's') and inner_ctx.s(0):
            num_statements = 1
            if hasattr(inner_ctx, 'SEMI') and inner_ctx.SEMI(): num_statements += len(inner_ctx.SEMI())
        for i in range(num_statements):
            statement_ctx = inner_ctx.s(i)
            if statement_ctx: self.visit(statement_ctx)
        return None
    def visitIf(self, ctx: WhileParser.IfContext):
        inner_ctx = ctx.if_stmt();
        if inner_ctx is None: runtime_error("Internal Error: Missing if_stmt context.")
        condition = self.visit(inner_ctx.e())
        if get_value_type(condition) != 'bool': runtime_error(f"If condition must evaluate to boolean, got {get_value_type(condition)}")
        if condition: self.visit(inner_ctx.s(0))
        elif inner_ctx.s(1): self.visit(inner_ctx.s(1))
        return None
    def visitWhile(self, ctx: WhileParser.WhileContext):
        inner_ctx = ctx.while_stmt();
        if inner_ctx is None: runtime_error("Internal Error: Missing while_stmt context.")
        while True:
            condition = self.visit(inner_ctx.e())
            if get_value_type(condition) != 'bool': runtime_error(f"While condition must evaluate to boolean, got {get_value_type(condition)}")
            if not condition: break
            self.visit(inner_ctx.s()) # Use s() here
        return None
    def visitEBinOpAndOr(self, ctx: WhileParser.EBinOpAndOrContext):
        left = self.visit(ctx.e(0))
        if get_value_type(left) != 'bool': runtime_error(f"Left operand for '{ctx.op.text}' must be boolean.")
        if ctx.op.text == 'and' and not left: return False
        if ctx.op.text == 'or' and left: return True
        right = self.visit(ctx.e(1))
        if get_value_type(right) != 'bool': runtime_error(f"Right operand for '{ctx.op.text}' must be boolean.")
        return left and right if ctx.op.text == 'and' else left or right
    def visitEComp(self, ctx: WhileParser.ECompContext): return self.visit(ctx.compExpr())
    def visitEBinOpComp(self, ctx: WhileParser.EBinOpCompContext):
        left = self.visit(ctx.compExpr(0))
        right = self.visit(ctx.compExpr(1))
        op = ctx.op.text
        if get_value_type(left) != get_value_type(right): runtime_error(f"Cannot compare values of different types: {get_value_type(left)} {op} {get_value_type(right)}")
        if op in ['<', '<=', '>', '>='] and get_value_type(left) != 'int': runtime_error(f"Comparison operator '{op}' only supports integers, got {get_value_type(left)}.")
        ops = {'<': lambda a, b: a < b, '<=': lambda a, b: a <= b, '=': lambda a, b: a == b, '>': lambda a, b: a > b, '>=': lambda a, b: a >= b}
        if op not in ops: runtime_error(f"Unknown comparison operator: {op}")
        return ops[op](left, right)
    def visitEAdd(self, ctx: WhileParser.EAddContext): return self.visit(ctx.addExpr())
    def visitEBinOpAddSub(self, ctx: WhileParser.EBinOpAddSubContext):
        left = self.visit(ctx.addExpr(0))
        right = self.visit(ctx.addExpr(1))
        op = ctx.op.text
        if get_value_type(left) != 'int' or get_value_type(right) != 'int': runtime_error(f"Cannot perform arithmetic ({op}) on non-integers: {type(left).__name__} {op} {type(right).__name__}")
        return (left + right) if op == '+' else (left - right)
    def visitEMult(self, ctx: WhileParser.EMultContext): return self.visit(ctx.multExpr())
    def visitEBinOpMulDiv(self, ctx: WhileParser.EBinOpMulDivContext):
        left = self.visit(ctx.multExpr(0))
        right = self.visit(ctx.multExpr(1))
        op = ctx.op.text
        if get_value_type(left) != 'int' or get_value_type(right) != 'int': runtime_error(f"Cannot perform arithmetic ({op}) on non-integers: {type(left).__name__} {op} {type(right).__name__}")
        if op == '*': return left * right
        elif op == '/':
            if right == 0: runtime_error("Division by zero.")
            return left // right # Integer division
        else: runtime_error(f"Unknown mul/div operator: {op}")
    def visitEUnary(self, ctx: WhileParser.EUnaryContext): return self.visit(ctx.unaryExpr())
    def visitENot(self, ctx: WhileParser.ENotContext):
        val = self.visit(ctx.unaryExpr())
        if get_value_type(val) != 'bool': runtime_error(f"'not' operand must be boolean, got {type(val).__name__}")
        return not val
    def visitEPrimary(self, ctx: WhileParser.EPrimaryContext): return self.visit(ctx.primaryExpr())
    def visitTrue(self, ctx: WhileParser.TrueContext): return True
    def visitFalse(self, ctx: WhileParser.FalseContext): return False
    def visitVar(self, ctx: WhileParser.VarContext):
        var_name = ctx.ID().getText()
        if var_name not in symtab: runtime_error(f"Variable '{var_name}' not declared.")
        var_info = symtab[var_name]
        if var_info['type'] == 'array': runtime_error(f"Type Error: Cannot use array variable '{var_name}' directly as a value.")
        return var_info['value']
    def visitNum(self, ctx: WhileParser.NumContext): return int(ctx.NUM().getText())
    def visitArrayAccess(self, ctx: WhileParser.ArrayAccessContext):
        array_name = ctx.ID().getText()
        if array_name not in symtab: runtime_error(f"Array variable '{array_name}' not declared.")
        array_info = symtab[array_name]
        if array_info['type'] != 'array': runtime_error(f"Type Error: Variable '{array_name}' is not an array.")
        index_value = self.visit(ctx.e())
        if not isinstance(index_value, int): runtime_error(f"Array index for '{array_name}' must be an integer, got {type(index_value).__name__}")
        array_size = array_info['size']
        if not (0 <= index_value < array_size): runtime_error(f"Array index out of bounds for '{array_name}': index={index_value}, size={array_size}.")
        element_type = array_info['element_type']
        return array_info['value'].get(index_value, DEFAULT_VALUES[element_type])
    def visitParen(self, ctx: WhileParser.ParenContext): return self.visit(ctx.e())


# --- Main Execution Logic ---
if __name__ == "__main__":
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
         sys.stderr.write(f"Error during parsing setup or start rule invocation: {e}\n")
         exit(1)

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors detected during parsing.", file=sys.stderr)
        exit(1)

    interpreter = Interpreter()
    try:
        symtab = {} # Clear symbol table before run
        interpreter.visit(tree)
    except SystemExit:
        exit(1)
    except Exception as e:
        import traceback
        sys.stderr.write(f"Unexpected Interpreter Error: {e}\n")
        sys.stderr.write(traceback.format_exc())
        exit(1)

    # --- Print the final symbol table ---
    print("--- Final Symbol Table ---")
    if not symtab:
        print("(empty)")
    else:
        output_lines = []
        for name in sorted(symtab.keys()):
            info = symtab[name]
            var_type = info['type']
            value = info['value']
            if var_type == 'array':
                element_type = info['element_type']
                size = info['size']
                array_items = ", ".join([f"{idx}: {val}" for idx, val in sorted(value.items())])
                output_lines.append(f"symtab[\"{name}\"] ({var_type}[{size}] of {element_type}): {{{array_items}}}")
            else: # int or bool
                 output_lines.append(f"symtab[\"{name}\"] ({var_type}): {value}")
        print("\n".join(output_lines))