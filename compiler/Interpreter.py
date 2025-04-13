import sys
from antlr4 import *
sys.path.append('./') # Ensure Python can find grammar files
# Import generated files based on the FINAL grammar
from grammar.WhileLexer import WhileLexer
from grammar.WhileParser import WhileParser
from grammar.WhileVisitor import WhileVisitor

# --- Symbol table ---
# Can store integers for simple vars, or dictionaries {index: value} for arrays
symtab = {}

# --- Runtime Error Helper ---
def runtime_error(msg):
    """Prints a runtime error message to stderr and exits."""
    sys.stderr.write(f"Runtime Error: {msg}\n")
    sys.exit(1)

# --- Interpreter Visitor ---
class Interpreter(WhileVisitor):

    # --- Statement Visitors (Matching Labels in 's') ---

    # Handles both SimpleAssignment and ArrayElementAssignment via labels
    def visitAssignmentStmt(self, ctx: WhileParser.AssignmentStmtContext):
        """ Visits the wrapper AssignmentStmt node and delegates based on inner type. """
        assignment_ctx = ctx.assignment() # Get the specific assignment type node

        # --- Handle Simple Assignment ---
        if isinstance(assignment_ctx, WhileParser.SimpleAssignmentContext):
            var_name = assignment_ctx.ID().getText()
            value = self.visit(assignment_ctx.a())

            # Basic Runtime Type Check: Ensure we assign integers to simple vars
            # (Adjust if your language allows other scalar types)
            if not isinstance(value, int):
                 runtime_error(f"Attempting to assign non-integer value of type {type(value)} to simple variable '{var_name}'.")

            # Check if var_name currently holds an array - prevent overwriting array with scalar
            if var_name in symtab and isinstance(symtab[var_name], dict):
                runtime_error(f"Type Error: Cannot assign simple value to variable '{var_name}' which is currently an array.")

            symtab[var_name] = value
            # Return value (optional, depends if assignment is an expression)
            return value

        # --- Handle Array Element Assignment ---
        elif isinstance(assignment_ctx, WhileParser.ArrayElementAssignmentContext):
            array_name = assignment_ctx.ID().getText()
            index_expr_val = self.visit(assignment_ctx.a(0)) # Evaluate index expression
            value_expr_val = self.visit(assignment_ctx.a(1)) # Evaluate value expression

            # Runtime Type Check: Index must be an integer
            if not isinstance(index_expr_val, int):
                runtime_error(f"Array index for '{array_name}' must be an integer, got {type(index_expr_val)}")

            # Runtime Type Check: Value assigned to element must be integer
            # (Adjust if your arrays can hold other types)
            if not isinstance(value_expr_val, int):
                 runtime_error(f"Attempting to assign non-integer value of type {type(value_expr_val)} to element of array '{array_name}'.")

            # Check if variable exists and is an array (dictionary)
            if array_name not in symtab:
                symtab[array_name] = {} # Auto-initialize array if it doesn't exist
            elif not isinstance(symtab[array_name], dict):
                runtime_error(f"Type Error: Variable '{array_name}' is not an array.")

            # Assign value to the index in the array's dictionary
            symtab[array_name][index_expr_val] = value_expr_val
             # Return value (optional)
            return value_expr_val
        else:
             # Should not happen if grammar and visitor are correct
             runtime_error("Internal error: Unknown assignment context type.")
             return None

    def visitSkip(self, ctx: WhileParser.SkipContext):
        """ Visits skip statement - does nothing. """
        return None # No operation

    def visitCompound(self, ctx: WhileParser.CompoundContext):
        """ Visits a begin...end block, executing statements sequentially. """
        for statement in ctx.s(): # Iterate through statement children ('s' rule)
            self.visit(statement) # Visit each statement
        return None

    def visitIf(self, ctx: WhileParser.IfContext):
        """ Visits an if-then-else statement. """
        condition = self.visit(ctx.b()) # Evaluate the boolean condition
        # Runtime Type Check: Condition must be boolean
        if not isinstance(condition, bool):
             runtime_error(f"If condition must evaluate to boolean, got {type(condition)}")

        if condition:
            self.visit(ctx.s(0)) # Execute 'then' block statement (s at index 0)
        elif ctx.s(1): # Check if 'else' block exists (s at index 1)
            self.visit(ctx.s(1)) # Execute 'else' block statement
        return None

    def visitWhile(self, ctx: WhileParser.WhileContext):
        """ Visits a while loop. """
        while True:
            condition = self.visit(ctx.b()) # Evaluate condition
            # Runtime Type Check: Condition must be boolean
            if not isinstance(condition, bool):
                runtime_error(f"While condition must evaluate to boolean, got {type(condition)}")

            if not condition:
                break # Exit loop if condition is false

            self.visit(ctx.s()) # Execute loop body statement
        return None

    # --- Boolean Expression Visitors (Matching Labels in 'b') ---

    def visitTrue(self, ctx: WhileParser.TrueContext): return True
    def visitFalse(self, ctx: WhileParser.FalseContext): return False

    def visitNot(self, ctx: WhileParser.NotContext):
        val = self.visit(ctx.b())
        if not isinstance(val, bool): runtime_error(f"'not' operand must be boolean, got {type(val)}")
        return not val

    def visitAnd(self, ctx: WhileParser.AndContext):
        left = self.visit(ctx.b(0))
        if not isinstance(left, bool): runtime_error(f"'and' left operand must be boolean, got {type(left)}")
        if not left: return False # Short-circuit
        right = self.visit(ctx.b(1))
        if not isinstance(right, bool): runtime_error(f"'and' right operand must be boolean, got {type(right)}")
        return left and right

    def visitOr(self, ctx: WhileParser.OrContext):
        left = self.visit(ctx.b(0))
        if not isinstance(left, bool): runtime_error(f"'or' left operand must be boolean, got {type(left)}")
        if left: return True # Short-circuit
        right = self.visit(ctx.b(1))
        if not isinstance(right, bool): runtime_error(f"'or' right operand must be boolean, got {type(right)}")
        return left or right

    def visitROp(self, ctx: WhileParser.ROpContext):
        left = self.visit(ctx.a(0))
        right = self.visit(ctx.a(1))
        op = ctx.op.text # Get operator from labeled token

        # Runtime Type Check: Operands must be integers for comparison
        if not isinstance(left, int) or not isinstance(right, int):
             runtime_error(f"Cannot compare non-integers: {type(left)} {op} {type(right)}")

        if op == '<': return left < right
        elif op == '<=': return left <= right
        elif op == '=': return left == right
        elif op == '>': return left > right
        elif op == '>=': return left >= right
        else: runtime_error(f"Unknown relational operator: {op}")

    def visitBParen(self, ctx: WhileParser.BParenContext):
        return self.visit(ctx.b()) # Evaluate inner boolean expression

    # --- Arithmetic Expression Visitors (Matching Labels in 'a', 'a_term', 'a_factor') ---

    def visitAOpAddSub(self, ctx: WhileParser.AOpAddSubContext):
        left = self.visit(ctx.a())     # Visit lower precedence 'a'
        right = self.visit(ctx.a_term()) # Visit higher precedence 'a_term'
        op = ctx.op.text

        # Runtime Type Check: Operands must be integers
        if not isinstance(left, int) or not isinstance(right, int):
             runtime_error(f"Cannot perform arithmetic on non-integers: {type(left)} {op} {type(right)}")

        if op == '+': return left + right
        elif op == '-': return left - right
        else: runtime_error(f"Unknown add/sub operator: {op}")

    def visitATerm(self, ctx: WhileParser.ATermContext):
        # Pass visit down to the 'a_term' child (handles precedence)
        return self.visit(ctx.a_term())

    def visitAOpMulDiv(self, ctx: WhileParser.AOpMulDivContext):
        left = self.visit(ctx.a_term())  # Visit higher precedence 'a_term'
        right = self.visit(ctx.a_factor())# Visit highest precedence 'a_factor'
        op = ctx.op.text

        # Runtime Type Check: Operands must be integers
        if not isinstance(left, int) or not isinstance(right, int):
             runtime_error(f"Cannot perform arithmetic on non-integers: {type(left)} {op} {type(right)}")

        if op == '*': return left * right
        elif op == '/':
            if right == 0: runtime_error("Division by zero.")
            return left // right # Integer division
        else: runtime_error(f"Unknown mul/div operator: {op}")

    def visitAFactor(self, ctx: WhileParser.AFactorContext):
         # Pass visit down to the 'a_factor' child (handles precedence)
        return self.visit(ctx.a_factor())

    # --- Factor Level Visitors (Matching Labels in 'a_factor') ---

    def visitVar(self, ctx: WhileParser.VarContext):
        """ Handles simple variable access like 'x'. """
        var_name = ctx.ID().getText()
        if var_name not in symtab:
            # Auto-initialize simple variables to 0 on first read
            symtab[var_name] = 0
            return 0
        # Runtime Type Check: Ensure it's not an array being used as scalar
        elif isinstance(symtab[var_name], dict):
            runtime_error(f"Type Error: Cannot use array '{var_name}' as a simple variable value.")
        # Runtime Type Check: Ensure it's an integer (or other allowed scalar type)
        elif not isinstance(symtab[var_name], int):
             runtime_error(f"Type Error: Variable '{var_name}' holds unexpected type {type(symtab[var_name])}.")
        else:
            # It's a simple variable (integer)
            return symtab[var_name]

    def visitNum(self, ctx: WhileParser.NumContext):
        """ Handles integer literals. """
        return int(ctx.NUM().getText())

    def visitArrayAccess(self, ctx: WhileParser.ArrayAccessContext):
        """ Handles array element access like 'a[i]'. """
        array_name = ctx.ID().getText()
        index_expr_val = self.visit(ctx.a()) # Evaluate index expression

        # Runtime Type Check: Index must be integer
        if not isinstance(index_expr_val, int):
                runtime_error(f"Array index for '{array_name}' must be an integer, got {type(index_expr_val)}")

        # Check if variable exists
        if array_name not in symtab:
             # Array doesn't exist, reading element defaults to 0
             # Alternative: could auto-initialize symtab[array_name] = {} here
             return 0
        # Runtime Type Check: Ensure it's actually an array
        elif not isinstance(symtab[array_name], dict):
             runtime_error(f"Type Error: Variable '{array_name}' is not an array.")
        else:
             # It is an array (dictionary), get value at index.
             # Default to 0 if index hasn't been assigned yet.
             element_value = symtab[array_name].get(index_expr_val, 0)
             # Runtime Type Check: Ensure element is integer (if arrays are int-only)
             if not isinstance(element_value, int):
                  runtime_error(f"Type Error: Array element '{array_name}[{index_expr_val}]' holds non-integer type {type(element_value)}.")
             return element_value

    def visitAParen(self, ctx: WhileParser.AParenContext):
        """ Handles parentheses in arithmetic expressions. """
        return self.visit(ctx.a()) # Evaluate inner expression


# --- Main Execution Logic ---
if __name__ == "__main__":
    input_text = sys.stdin.read().strip()

    # Auto-wrap in begin/end if necessary
    if not (input_text.startswith("begin") and input_text.endswith("end")):
        input_text = f"begin\n{input_text}\nend"

    input_stream = InputStream(input_text)
    lexer = WhileLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = WhileParser(stream)
    parser.removeErrorListeners() # Remove default listener

    tree = parser.s() # Parse the program starting from rule 's'

    if parser.getNumberOfSyntaxErrors() > 0:
        # Exit if syntax errors occurred (ANTLR usually prints them by default)
        print("Syntax errors detected during parsing.", file=sys.stderr)
        exit(1)

    # Execute the program using the interpreter visitor
    interpreter = Interpreter()
    try:
        interpreter.visit(tree)
    except SystemExit: # Catch exit calls from runtime_error
        exit(1)
    except Exception as e:
        # Catch other potential visitor errors
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
        # Sort by variable name for consistent output
        for name in sorted(symtab.keys()):
            value = symtab[name]
            if isinstance(value, dict): # It's an array
                # Format array content, sort by index
                array_items = ", ".join([f"{idx}: {val}" for idx, val in sorted(value.items())])
                output_lines.append(f"symtab[\"{name}\"] (array): {{{array_items}}}")
            elif isinstance(value, int): # It's an integer
                 output_lines.append(f"symtab[\"{name}\"] (int): {value}")
            else: # Should not happen with current checks, but good fallback
                 output_lines.append(f"symtab[\"{name}\"] (unknown type - {type(value)}): {value}")
        print("\n".join(output_lines))