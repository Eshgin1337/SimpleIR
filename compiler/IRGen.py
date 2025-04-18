import sys
from antlr4 import *
from antlr4 import ParserRuleContext
from antlr4.error.ErrorListener import ErrorListener
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
        print("Error: Could not import ANTLR generated files.", file=sys.stderr)
        print("Ensure 'WhileLexer.py', 'WhileParser.py', and 'WhileVisitor.py' exist", file=sys.stderr)
        print("and are accessible in the Python path (e.g., in './grammar/' or current dir).", file=sys.stderr)
        print(f"Original error: {e}", file=sys.stderr)
        sys.exit(1)

import logging
from textwrap import dedent
from io import StringIO
from contextlib import contextmanager
import io
import os


@contextmanager
def suppress_stderr():
    """Temporarily suppress stderr to hide ANTLR messages if needed (use with caution)."""
    try:
        original_stderr_fd = sys.stderr.fileno()
    except (AttributeError, OSError, io.UnsupportedOperation):
        yield
        return
    saved_stderr_fd = os.dup(original_stderr_fd)
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, original_stderr_fd)
        os.close(devnull_fd)
        yield
    finally:
        try:
            os.dup2(saved_stderr_fd, original_stderr_fd)
            os.close(saved_stderr_fd)
        except OSError:
            pass

INDENT = "  "

class CompilerError(Exception):
    """Custom exception for compiler-specific errors."""
    pass

def panic(message):
    """Raises a CompilerError, stopping the compilation process."""
    raise CompilerError(message)

class SyntaxErrListener(ErrorListener):
    """Custom ANTLR error listener to collect syntax errors."""
    def __init__(self):
        super().__init__()
        self.error_count = 0
        self.error_messages = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Callback for ANTLR syntax errors."""
        self.error_count += 1
        self.error_messages.append(f"Syntax error at line {line}:{column} - {msg}")


class IRGen(WhileVisitor):
    """
    ANTLR Visitor that walks the While language parse tree and generates SimpleIR code.
    Visitor method names match the # labels in the While.g4 grammar.
    """
    def __init__(self, outfile=sys.stdout):
        """
        Initializes the IR Generator.

        Args:
            outfile: The file-like object (e.g., sys.stdout, StringIO) to write the IR code to.
        """
        self.outfile = outfile
        self.labelnum = 0
        self.varnum = 0
        self.symtab = {}
        self.scalar_vars = set()
        self.element_size = 1

    def freshlabel(self):
        """Generates a new unique label name."""
        self.labelnum += 1
        return f'L{self.labelnum}'

    def freshvar(self):
        """Generates a new unique temporary variable name."""
        self.varnum += 1
        return f'_t{self.varnum}'

    def emit(self, code_str):
        """
        Writes a line of SimpleIR code to the output buffer.
        Dedents the input string and prints non-empty lines.
        Indentation is handled later when assembling the function body.
        """
        base_code = dedent(code_str).strip()
        if base_code:
            for line in base_code.splitlines():
                 print(f"{line}", file=self.outfile)

    def get_var_info(self, name, context_for_error_msg=""):
        """
        Retrieves variable information from the symbol table.
        Panics if the variable is not declared.

        Args:
            name: The name of the variable.
            context_for_error_msg: The ANTLR context node (optional) for better error messages.

        Returns:
            The dictionary containing the variable's info from the symbol table.
        """
        if name not in self.symtab:
            location = f" near line {context_for_error_msg.start.line}" if hasattr(context_for_error_msg, 'start') else ""
            panic(f"Compiler Error: Variable '{name}' used before declaration{location}.")
        return self.symtab[name]

    def ensure_name(self, value_or_name, setup_code):
        """
        Ensures a value is represented by a variable name (NAME token in SimpleIR).
        If the input is a literal (e.g., '5', 'true'), it generates code to load
        the literal into a fresh temporary variable and returns the temporary's name.
        If the input is already a variable name (including temps like _t1), it returns the name directly.

        Args:
            value_or_name: A string which is either a variable name or a literal value.
            setup_code: Existing IR code generated for evaluating this value (if any).

        Returns:
            A tuple: (variable_name, combined_setup_code).
            'variable_name' is guaranteed to be a valid SimpleIR NAME (original or temporary).
            'combined_setup_code' includes original setup code plus any new code for temp loading.
        """
        is_literal_num = value_or_name.isdigit() or (value_or_name.startswith('-') and value_or_name[1:].isdigit())
        is_bool_literal = value_or_name in ['true', 'false']
        is_valid_identifier = value_or_name.isidentifier()

        if not is_valid_identifier:
            if not (is_literal_num or is_bool_literal):
                 panic(f"Internal Error: Invalid value '{value_or_name}' encountered in ensure_name.")

            temp = self.freshvar()
            value_to_assign = value_or_name
            if is_bool_literal:
                value_to_assign = '1' if value_or_name == 'true' else '0'

            new_code = f"{temp} := {value_to_assign}"
            combined_code = f"{setup_code}\n{new_code}".strip() if setup_code else new_code
            return (temp, combined_code)
        else:
            return (value_or_name, setup_code)

    def visitDeclarationStmt(self, ctx: WhileParser.DeclarationStmtContext):
        """Handles variable and array declarations via the #DeclarationStmt label."""
        decl_ctx = ctx.declaration()
        if decl_ctx is None: panic("IR Gen Internal Error: Missing declaration context.")

        var_name = decl_ctx.ID().getText()
        type_name = decl_ctx.typeName.text

        if var_name in self.symtab:
            panic(f"Compiler Error: Variable '{var_name}' already declared near line {ctx.start.line}.")

        size_ctx = decl_ctx.size

        if size_ctx: # Array Declaration
            try:
                size = int(size_ctx.text)
                if size <= 0:
                    panic(f"Compiler Error: Array size must be positive for '{var_name}' near line {ctx.start.line}.")
            except ValueError:
                panic(f"Compiler Error: Invalid array size '{size_ctx.text}' for '{var_name}' near line {ctx.start.line}.")

            self.symtab[var_name] = {'type': 'array', 'size': size, 'element_type': type_name}
            logging.debug(f"IRGen Symtab: Declared array {var_name}[{size}] of {type_name}")
            self.emit(f"alloc {var_name}, {size}")

        else: # Scalar Variable Declaration
            self.symtab[var_name] = {'type': type_name, 'size': None, 'element_type': None}
            self.scalar_vars.add(var_name)
            logging.debug(f"IRGen Symtab: Declared {type_name} {var_name}")

        return None

    def visitAssignmentStmt(self, ctx: WhileParser.AssignmentStmtContext):
        """Handles assignment statements via the #AssignmentStmt label."""
        assign_ctx = ctx.assignment()
        if assign_ctx is None: panic("IR Gen Internal Error: Missing assignment context.")

        target_ctx = assign_ctx.assignTarget()
        rhs_temp_or_literal, rhs_code = self.visit(assign_ctx.e())
        rhs_var, rhs_setup_code = self.ensure_name(rhs_temp_or_literal, rhs_code)

        if isinstance(target_ctx, WhileParser.AssignVarTargetContext): # Scalar Assignment
            var_name = target_ctx.ID().getText()
            var_info = self.get_var_info(var_name, ctx)
            if var_info['type'] == 'array':
                panic(f"Compiler Type Error: Cannot assign scalar value to array variable '{var_name}' near line {ctx.start.line}.")

            self.emit(rhs_setup_code)
            self.emit(f"{var_name} := {rhs_var}")

        elif isinstance(target_ctx, WhileParser.AssignArrayTargetContext): # Array Element Assignment
            array_name = target_ctx.ID().getText()
            array_info = self.get_var_info(array_name, ctx)
            if array_info['type'] != 'array':
                panic(f"Compiler Type Error: Variable '{array_name}' is not an array near line {ctx.start.line}.")

            index_temp_or_literal, index_code = self.visit(target_ctx.e())
            index_var, index_setup_code = self.ensure_name(index_temp_or_literal, index_code)

            addr_temp = self.freshvar()
            addr_calc_code = f"{addr_temp} := addr {array_name}, {index_var}"
            store_code = f"store {rhs_var}, {addr_temp}"

            self.emit(index_setup_code)
            self.emit(rhs_setup_code)
            self.emit(addr_calc_code)
            self.emit(store_code)
        else:
            panic(f"Internal error: Unknown assignment target context type: {type(target_ctx)}")

        return None

    def visitSkip(self, ctx: WhileParser.SkipContext):
        """Handles the 'skip' statement via the #Skip label."""
        self.emit("# skip")
        return None

    def visitCompound(self, ctx: WhileParser.CompoundContext):
        """Handles compound statements { s1; s2; ... } via the #Compound label."""
        compound_stmt_ctx = ctx.compound_stmt()
        if compound_stmt_ctx is None: panic("IR Gen Internal Error: Missing compound_stmt context.")
        if hasattr(compound_stmt_ctx, 's') and compound_stmt_ctx.s():
             num_statements = len(compound_stmt_ctx.s())
             for i in range(num_statements):
                 statement_ctx = compound_stmt_ctx.s(i)
                 if statement_ctx:
                     self.visit(statement_ctx)
        return None

    def visitIf(self, ctx: WhileParser.IfContext):
        """Handles 'if condition then s1 else s2' statements via the #If label."""
        if_stmt_ctx = ctx.if_stmt()
        if if_stmt_ctx is None: panic("IR Gen Internal Error: Missing if_stmt context.")

        cond_temp_or_literal, cond_code = self.visit(if_stmt_ctx.e())
        cond_var, cond_setup_code = self.ensure_name(cond_temp_or_literal, cond_code)

        else_label = self.freshlabel()
        end_label = self.freshlabel()

        self.emit(cond_setup_code)
        self.emit(f"if {cond_var} = 0 goto {else_label}")

        self.visit(if_stmt_ctx.s(0))
        self.emit(f"goto {end_label}")

        self.emit(f"{else_label}:")
        self.visit(if_stmt_ctx.s(1))

        self.emit(f"{end_label}:")
        return None

    def visitWhile(self, ctx: WhileParser.WhileContext):
        """Handles 'while condition do s' statements via the #While label."""
        while_stmt_ctx = ctx.while_stmt()
        if while_stmt_ctx is None: panic("IR Gen Internal Error: Missing while_stmt context.")

        head_label = self.freshlabel()
        end_label = self.freshlabel()

        self.emit(f"{head_label}:")

        cond_temp_or_literal, cond_code = self.visit(while_stmt_ctx.e())
        cond_var, cond_setup_code = self.ensure_name(cond_temp_or_literal, cond_code)

        self.emit(cond_setup_code)
        self.emit(f"if {cond_var} = 0 goto {end_label}")

        self.visit(while_stmt_ctx.s())
        self.emit(f"goto {head_label}")

        self.emit(f"{end_label}:")
        return None

    def _visitDirectBinaryOp(self, ctx, rule_getter_func, op_text_override=None):
        """
        Helper for binary operations (+, -, *, /) that directly map to SimpleIR operations.
        Ensures both operands are NAMEs before emitting the operation.
        """
        left_val_or_name, left_code = self.visit(rule_getter_func(ctx, 0))
        right_val_or_name, right_code = self.visit(rule_getter_func(ctx, 1))

        left_var, setup_code1 = self.ensure_name(left_val_or_name, left_code)
        right_var, setup_code2 = self.ensure_name(right_val_or_name, right_code)

        op = op_text_override if op_text_override else ctx.op.text

        result_temp = self.freshvar()
        op_ir = f"{result_temp} := {left_var} {op} {right_var}"

        full_code = f"{setup_code1}\n{setup_code2}\n{op_ir}".strip()
        return (result_temp, full_code)

    def visitEBinOpAndOr(self, ctx: WhileParser.EBinOpAndOrContext):
        """Handles logical AND and OR using short-circuiting logic with jumps."""
        left_val_or_name, left_code = self.visit(ctx.e(0))
        left_var, setup_code1 = self.ensure_name(left_val_or_name, left_code)

        result_temp = self.freshvar()
        op = ctx.op.text
        end_label = self.freshlabel()
        code = setup_code1

        if op == 'or':
            set_true_label = self.freshlabel()
            code += f"\nif {left_var} != 0 goto {set_true_label}"
            right_val_or_name, right_setup = self.visit(ctx.e(1))
            right_var, setup_code2 = self.ensure_name(right_val_or_name, right_setup)
            code += f"\n{setup_code2}"
            code += f"\nif {right_var} != 0 goto {set_true_label}"
            code += f"\n{result_temp} := 0"
            code += f"\ngoto {end_label}"
            code += f"\n{set_true_label}:"
            code += f"\n{result_temp} := 1"
            code += f"\n{end_label}:"
        elif op == 'and':
            set_false_label = self.freshlabel()
            code += f"\nif {left_var} = 0 goto {set_false_label}"
            right_val_or_name, right_setup = self.visit(ctx.e(1))
            right_var, setup_code2 = self.ensure_name(right_val_or_name, right_setup)
            code += f"\n{setup_code2}"
            code += f"\nif {right_var} = 0 goto {set_false_label}"
            code += f"\n{result_temp} := 1"
            code += f"\ngoto {end_label}"
            code += f"\n{set_false_label}:"
            code += f"\n{result_temp} := 0"
            code += f"\n{end_label}:"
        else:
            panic(f"Unknown boolean operator '{op}' near line {ctx.start.line}")
        return (result_temp, code.strip())

    def visitEComp(self, ctx: WhileParser.ECompContext):
        """Passes visit down to comparison expression."""
        return self.visit(ctx.compExpr())

    def visitEBinOpComp(self, ctx: WhileParser.EBinOpCompContext):
        """Handles comparison operators (==, !=, <, <=, >, >=)."""
        left_val_or_name, left_code = self.visit(ctx.compExpr(0))
        right_val_or_name, right_code = self.visit(ctx.compExpr(1))

        left_var, setup_code1 = self.ensure_name(left_val_or_name, left_code)
        right_var, setup_code2 = self.ensure_name(right_val_or_name, right_code)

        op = ctx.op.text
        result_temp = self.freshvar()
        set_true_label = self.freshlabel()
        end_label = self.freshlabel()
        code = f"{setup_code1}\n{setup_code2}".strip()
        code += f"\nif {left_var} {op} {right_var} goto {set_true_label}"
        code += f"\n{result_temp} := 0"
        code += f"\ngoto {end_label}"
        code += f"\n{set_true_label}:"
        code += f"\n{result_temp} := 1"
        code += f"\n{end_label}:"
        return (result_temp, code.strip())

    def visitEAdd(self, ctx: WhileParser.EAddContext):
        """Passes visit down to additive expression."""
        return self.visit(ctx.addExpr())

    def visitEBinOpAddSub(self, ctx: WhileParser.EBinOpAddSubContext):
        """Handles addition (+) and subtraction (-)."""
        return self._visitDirectBinaryOp(ctx, lambda c, i: c.addExpr(i))

    def visitEMult(self, ctx: WhileParser.EMultContext):
        """Passes visit down to multiplicative expression."""
        return self.visit(ctx.multExpr())

    def visitEBinOpMulDiv(self, ctx: WhileParser.EBinOpMulDivContext):
        """Handles multiplication (*) and division (/)."""
        op_symbol = ctx.op.text
        return self._visitDirectBinaryOp(ctx, lambda c, i: c.multExpr(i), op_text_override=op_symbol)

    def visitEUnary(self, ctx: WhileParser.EUnaryContext):
        """Passes visit down to unary expression."""
        return self.visit(ctx.unaryExpr())

    def visitENot(self, ctx: WhileParser.ENotContext):
        """Handles logical NOT (!). Assumes boolean is 0 or 1."""
        operand_val_or_name, operand_code = self.visit(ctx.unaryExpr())
        operand_var, setup_code = self.ensure_name(operand_val_or_name, operand_code)

        result_temp = self.freshvar()
        one_temp = self.freshvar()
        code = setup_code
        code += f"\n{one_temp} := 1"
        code += f"\n{result_temp} := {one_temp} - {operand_var}"
        return (result_temp, code.strip())

    def visitEPrimary(self, ctx: WhileParser.EPrimaryContext):
        """Passes visit down to primary expression (literals, vars, array access, parens)."""
        return self.visit(ctx.primaryExpr())

    def visitTrue(self, ctx: WhileParser.TrueContext):
        """Handles the 'true' literal via the #True label."""
        return ('true', "")

    def visitFalse(self, ctx: WhileParser.FalseContext):
        """Handles the 'false' literal via the #False label."""
        return ('false', "")

    def visitVar(self, ctx: WhileParser.VarContext):
        """Handles variable access via the #Var label."""
        var_name = ctx.ID().getText()
        var_info = self.get_var_info(var_name, ctx)
        if var_info['type'] == 'array':
            panic(f"Compiler Type Error: Cannot use array variable '{var_name}' directly as a value near line {ctx.start.line}.")
        return (var_name, "")

    def visitNum(self, ctx: WhileParser.NumContext):
        """Handles integer literals via the #Num label."""
        num_text = ctx.NUM().getText()
        return (num_text, "")

    def visitArrayAccess(self, ctx: WhileParser.ArrayAccessContext):
        """Handles array element access (e.g., a[i]) via the #ArrayAccess label."""
        array_name = ctx.ID().getText()
        array_info = self.get_var_info(array_name, ctx)
        if array_info['type'] != 'array':
            panic(f"Compiler Type Error: Variable '{array_name}' is not an array near line {ctx.start.line}.")

        index_val_or_name, index_code = self.visit(ctx.e())
        index_var, index_setup_code = self.ensure_name(index_val_or_name, index_code)

        addr_temp = self.freshvar()
        addr_calc_code = f"{addr_temp} := addr {array_name}, {index_var}"
        result_temp = self.freshvar()
        load_code = f"{result_temp} := load {addr_temp}"
        full_code = f"{index_setup_code}\n{addr_calc_code}\n{load_code}".strip()
        return (result_temp, full_code)

    def visitParen(self, ctx: WhileParser.ParenContext):
        """Handles parenthesized expressions via the #Paren label."""
        return self.visit(ctx.e())

def irgen(input_stream, output_stream):
    """
    Parses the input stream containing While code and writes SimpleIR to the output stream.

    Args:
        input_stream: An ANTLR InputStream (e.g., FileStream, InputStream).
        output_stream: A file-like object to write the generated IR code.
    """
    tree = None
    parser = None
    logging.debug("Initializing ANTLR components and parsing...")
    try:
        lexer = WhileLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = WhileParser(stream)
        parser.removeErrorListeners()
        error_listener = SyntaxErrListener()
        parser.addErrorListener(error_listener)

        entry_rule_name = 's'
        if not hasattr(parser, entry_rule_name):
             entry_rule_name = 'program'
             if not hasattr(parser, entry_rule_name):
                  panic(f"Cannot find suitable entry rule ('s' or 'program') in parser. Check your While.g4 grammar.")
             else:
                  logging.warning(f"Using 'program' as entry rule. Ensure this is correct for your grammar.")
        else:
             logging.debug(f"Using entry rule: {entry_rule_name}")


        tree = getattr(parser, entry_rule_name)()

        if error_listener.error_count > 0:
             errors = "\n".join([f"- {msg}" for msg in error_listener.error_messages])
             panic(f"Syntax errors found in input:\n{errors}")

    except Exception as e:
        panic(f"Error during ANTLR initialization/parsing: {e}")

    if tree is None:
        panic("Parsing completed without errors, but no parse tree was generated.")
    else:
        logging.debug("Visiting parse tree to generate IR...")
        body_output = StringIO()
        translator = IRGen(body_output)
        try:
            translator.visit(tree)

        except CompilerError as ce:
            raise ce
        except Exception as e:
             import traceback
             panic(f"Unexpected error during IR Generation visit: {e}\n{traceback.format_exc()}")

        output_stream.write("function main\n")

        if translator.scalar_vars:
            sorted_vars = sorted(list(translator.scalar_vars))
            local_decl_line = f"{INDENT}local {', '.join(sorted_vars)}"
            output_stream.write(local_decl_line + "\n")

        body_code = body_output.getvalue()
        for line in body_code.strip().splitlines():
            output_stream.write(f"{INDENT}{line.strip()}\n")

        output_stream.write(f"{INDENT}return 0\n")
        output_stream.write("end function\n")
        logging.debug("Finished writing IR output.")

def main():
    """
    Main entry point for the IR generator script.
    Handles command-line arguments for input file or reads from stdin.
    """
    logging.basicConfig(level=logging.INFO)

    input_stream = None
    try:
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            if not os.path.exists(input_file):
                 print(f"Error: Input file not found: {input_file}", file=sys.stderr)
                 sys.exit(1)
            logging.info(f"Reading While input from file: {input_file}")
            input_stream = FileStream(input_file, encoding='utf-8')
        else:
            logging.info("Reading While input from stdin...")
            input_text = sys.stdin.read()
            input_stream = InputStream(input_text)

        irgen(input_stream, sys.stdout)

    except CompilerError as ce:
        sys.stderr.write(f"\nCompiler Error: {str(ce)}\n")
        sys.stderr.write("IR Generation failed.\n")
        sys.exit(1)
    except ImportError as ie:
         sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"\nUnexpected error during IR Generation: {str(e)}\n")
        import traceback
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()