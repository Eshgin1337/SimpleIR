import sys
from antlr4 import *
sys.path.append('./')
from grammar.WhileLexer import WhileLexer
from grammar.WhileParser import WhileParser
from grammar.WhileVisitor import WhileVisitor
import logging
from textwrap import indent, dedent

import sys
import os
from io import StringIO

from contextlib import contextmanager
import io 

@contextmanager
def suppress_stderr():
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
    pass

def panic(message):
    raise CompilerError(message)

class IRGen(WhileVisitor):
    """
    A visitor that compiles the While language into SimpleIR.
    Statement visitors return nothing (write directly to outfile).
    Expression visitors return a tuple: (variable_name, setup_code_string).
    variable_name holds the result of the expression at runtime.
    setup_code_string is the SimpleIR code needed to compute that result.
    """
    def __init__(self, outfile=sys.stdout): 
        self.outfile = outfile
        self.labelnum = 0
        self.varnum = 0

    def freshlabel(self):
        self.labelnum += 1
        return f'L{self.labelnum}' 

    def freshvar(self):
        self.varnum += 1
        return f'_t{self.varnum}' 

    def emit(self, code_str):
        """Helper to print indented code, handling multiple lines."""
        base_code = dedent(code_str).strip() 
        if base_code: 
            for line in base_code.splitlines():
                print(f"{INDENT}{line}", file=self.outfile)


    def visitAssignment(self, ctx:WhileParser.AssignmentContext):
        tempname, setup_code = self.visit(ctx.a())
        varname = ctx.ID().getText()
        self.emit(setup_code)
        self.emit(f"{varname} := {tempname}")
        return None

    def visitSkip(self, ctx:WhileParser.SkipContext):
        self.emit("# skip") 
        return None

    def visitIf(self, ctx:WhileParser.IfContext):
        cond_var, cond_code = self.visit(ctx.b())

        else_label = self.freshlabel()
        end_label = self.freshlabel()

        self.emit(cond_code)
        self.emit(f"if {cond_var} = 0 goto {else_label}")

        self.visit(ctx.s(0))
        self.emit(f"goto {end_label}") 

        self.emit(f"{else_label}:")
        self.visit(ctx.s(1)) 

        self.emit(f"{end_label}:")
        return None

    def visitWhile(self, ctx:WhileParser.WhileContext):
        head_label = self.freshlabel() 
        body_label = self.freshlabel() 
        end_label = self.freshlabel()  

        self.emit(f"{head_label}:") 

        cond_var, cond_code = self.visit(ctx.b())
        self.emit(cond_code)
        self.emit(f"if {cond_var} = 0 goto {end_label}")

        self.visit(ctx.s())
        self.emit(f"goto {head_label}")

        self.emit(f"{end_label}:")
        return None

    def visitCompound(self, ctx:WhileParser.CompoundContext):
        for child_statement in ctx.s():
            self.visit(child_statement)
        return None


    def visitTrue(self, ctx:WhileParser.TrueContext):
        varname = self.freshvar()
        code = f'{varname} := 1'
        return (varname, code)

    def visitFalse(self, ctx:WhileParser.FalseContext):
        varname = self.freshvar()
        code = f'{varname} := 0'
        return (varname, code)

    def visitNot(self, ctx:WhileParser.NotContext):
        operand_var, operand_code = self.visit(ctx.b())
        result_var = self.freshvar()
        is_true_label = self.freshlabel() 
        end_label = self.freshlabel()

        code = dedent(f'''\
        {operand_code}
        if {operand_var} != 0 goto {is_true_label}
        {result_var} := 1
        goto {end_label}
        {is_true_label}:
        {result_var} := 0
        {end_label}:''')
        return (result_var, code)

    def visitAnd(self, ctx:WhileParser.AndContext):
        left_var, left_code = self.visit(ctx.b(0))
        result_var = self.freshvar() # Holds final result
        check_right_label = self.freshlabel()
        set_false_label = self.freshlabel()
        end_label = self.freshlabel()

        code = dedent(f'''\
        {left_code}
        if {left_var} = 0 goto {set_false_label}
        ''')
        right_var, right_code = self.visit(ctx.b(1))
        code += dedent(f'''\
        {right_code}
        if {right_var} = 0 goto {set_false_label}
        ''') 
        code += dedent(f'''\
        {result_var} := 1
        goto {end_label}
        {set_false_label}:
        {result_var} := 0
        {end_label}:''')
        return (result_var, code)

    def visitOr(self, ctx:WhileParser.OrContext):
        left_var, left_code = self.visit(ctx.b(0))
        result_var = self.freshvar()
        check_right_label = self.freshlabel()
        set_true_label = self.freshlabel()
        end_label = self.freshlabel()

        code = dedent(f'''\
        {left_code}
        if {left_var} != 0 goto {set_true_label}
        ''') 
        right_var, right_code = self.visit(ctx.b(1))
        code += dedent(f'''\
        {right_code}
        if {right_var} != 0 goto {set_true_label}
        ''') 
        code += dedent(f'''\
        {result_var} := 0
        goto {end_label}
        {set_true_label}:
        {result_var} := 1
        {end_label}:''')
        return (result_var, code)

    def visitROp(self, ctx:WhileParser.ROpContext):
        temp_a1, code_a1 = self.visit(ctx.a(0))
        temp_a2, code_a2 = self.visit(ctx.a(1))
        op = ctx.op.text 
        result_var = self.freshvar()
        set_true_label = self.freshlabel()
        end_label = self.freshlabel()

        code = dedent(f'''\
        {code_a1}
        {code_a2}
        if {temp_a1} {op} {temp_a2} goto {set_true_label}
        {result_var} := 0
        goto {end_label}
        {set_true_label}:
        {result_var} := 1
        {end_label}:''')
        return (result_var, code)

    def visitBParen(self, ctx:WhileParser.BParenContext):
        return self.visit(ctx.b())


    def visitAOp(self, ctx:WhileParser.AOpContext):
        temp_a1, code_a1 = self.visit(ctx.a(0))
        temp_a2, code_a2 = self.visit(ctx.a(1))
        result_var = self.freshvar()
        op = ctx.op.text 

        lines = []
        if code_a1.strip(): lines.extend(dedent(code_a1).strip().splitlines())
        if code_a2.strip(): lines.extend(dedent(code_a2).strip().splitlines())
        lines.append(f"{result_var} := {temp_a1} {op} {temp_a2}")
        code = "\n".join(lines)
        return (result_var, code)

    def visitVar(self, ctx:WhileParser.VarContext):
        tempname = self.freshvar()
        varname = ctx.ID().getText()
        code = f'{tempname} := {varname}'
        return (tempname, code)

    def visitNum(self, ctx:WhileParser.NumContext):
        tempname = self.freshvar()
        num = ctx.NUM().getText()
        code = f'{tempname} := {num}'
        return (tempname, code)

    def visitAParen(self, ctx:WhileParser.AParenContext):
        return self.visit(ctx.a())


def irgen(input_stream, output_stream):
    tree = None
    parser = None
    logging.debug("Initializing ANTLR components and parsing (stderr suppressed)...")
    try:
        with suppress_stderr():
             lexer = WhileLexer(input_stream)
             stream = CommonTokenStream(lexer)
             parser = WhileParser(stream)
             tree = parser.s()
    except Exception as e:
         panic(f"Error during ANTLR initialization/parsing: {e}")

    logging.debug("...stderr restored.")

    if parser is None:
         panic("Parser object failed to initialize.")
    num_syntax_errors = parser.getNumberOfSyntaxErrors()
    if num_syntax_errors > 0:
        panic(f"Syntax errors ({num_syntax_errors}) found in While input.")
    elif tree is None:
         panic("Parsing completed without errors, but no parse tree was generated.")
    else:
        logging.debug("Visiting parse tree to generate IR...")
        body_output = StringIO()
        translator = IRGen(body_output)
        translator.visit(tree)
        body_code = body_output.getvalue()

        output_stream.write("function main\n")
        for line in body_code.strip().splitlines():
            print(f"{INDENT}{line.strip()}", file=output_stream)
        print(f"{INDENT}return 0", file=output_stream)
        output_stream.write("end function\n")
        logging.debug("Finished writing IR output.")


def main():

    with suppress_stderr():
        try:
            if len(sys.argv) > 1:
                logging.info(f"Reading While input from file: {sys.argv[1]}")
                input_stream = FileStream(sys.argv[1], encoding='utf-8')
            else:
                logging.info("Reading While input from stdin...")
                input_stream = StdinStream()

            irgen(input_stream, sys.stdout)

        except CompilerError as ce:
            sys.stderr.write(f"Compiler Error: {str(ce)}\n")
            sys.stderr.write("Compilation failed.\n")
            sys.exit(1)
        except ImportError as ie:
             sys.stderr.write(f"Import Error: {str(ie)}\n")
             sys.stderr.write("Ensure ANTLR grammar files are generated and path is correct.\n")
             sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"Unexpected error during IR Generation: {str(e)}\n")
            sys.exit(1)


if __name__ == '__main__':
    main()
