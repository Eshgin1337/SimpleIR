# Optimizer.py
# Performs liveness analysis and dead code elimination on SimpleIR code.
# Corrected handling of ANTLR contexts based on grammar labels (v6 - Final).

import os
import sys
# Add paths to import simpleir modules if necessary
# sys.path.append('./')
# sys.path.append('../')
import itertools
from collections import defaultdict, deque
from antlr4 import *
from antlr4.tree.Tree import TerminalNode # Import TerminalNode
from antlr4.error.ErrorListener import ErrorListener # Import base class for SyntaxErrListener

# Assuming simpleir package/directory is accessible
try:
    from simpleir.SimpleIRLexer import SimpleIRLexer
    from simpleir.SimpleIRParser import SimpleIRParser
    from simpleir.SimpleIRListener import SimpleIRListener
    # Import specific contexts for type checking and access
    from simpleir.SimpleIRParser import SimpleIRParser
except ImportError as e:
     print(f"Error importing SimpleIR modules: {e}", file=sys.stderr)
     print("Ensure simpleir directory is in the Python path or PYTHONPATH.", file=sys.stderr)
     sys.exit(1)

import logging
logging.basicConfig(level=logging.INFO) # Set to DEBUG for more verbose output

# NetworkX for CFG
try:
    import networkx as nx
except ImportError:
    logging.error("NetworkX library not found (pip install networkx). Cannot build CFG.")
    nx = None # Set nx to None if not available

# PyGraphviz for visualization (optional)
try:
    import pygraphviz
    from networkx.drawing.nx_agraph import to_agraph
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    logging.warning("PyGraphviz library not found. CFG visualization will be skipped.")
    GRAPHVIZ_AVAILABLE = False
    to_agraph = None # Define to avoid NameError later


# --- Syntax Error Listener Class ---
class SyntaxErrListener(ErrorListener):
    """Custom ANTLR listener to capture syntax errors."""
    def __init__(self):
        super().__init__()
        self.error_count = 0
        self.error_messages = []
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Callback for ANTLR syntax errors."""
        self.error_count += 1
        offending_text = f"'{offendingSymbol.text}'" if offendingSymbol else ""
        self.error_messages.append(f"Syntax error at line {line}:{column} near {offending_text} - {msg}")


# --- Helper Functions ---

def get_instruction_text(ctx):
    """Gets the raw text of an instruction context (StatementContext or ReturnStatementContext)."""
    if not ctx or not hasattr(ctx, 'start') or not ctx.start:
        return "<invalid context>"
    try:
        # Use the input stream associated with the start token
        return ctx.start.getInputStream().getText(ctx.start.start, ctx.stop.stop)
    except Exception as e:
        logging.error(f"Failed to get text for context type {type(ctx)}: {e}", exc_info=True)
        return "<error getting text>"

def safe_get_terminal_text(node):
     """Safely gets text from a TerminalNode using getText() or a Token using .text."""
     if isinstance(node, TerminalNode):
          return node.getText()
     elif node and hasattr(node, 'text') and not callable(node.text): # Check for Token
          return node.text
     # logging.warning(f"safe_get_terminal_text called on non-terminal/token node: {type(node)}")
     return None

def safe_get_operand_text(node):
     """Safely gets text from an operand node (Token assigned via label=...)."""
     # Operands like operand=(NAME|NUM) result in the Token being the payload
     if node and hasattr(node, 'symbol'): # If it's a TerminalNode wrapping the token
          return node.symbol.text
     elif node and hasattr(node, 'text') and not callable(node.text): # If it's the token itself
          return node.text
     elif isinstance(node, TerminalNode): # Fallback if it was parsed as TerminalNode directly
          return node.getText()
     # logging.warning(f"safe_get_operand_text called on unexpected node type: {type(node)}")
     return None

def is_name_token(node):
    """Checks if a node represents a NAME token."""
    token_type = -1
    # Check if it's a TerminalNode wrapping a token
    if node and hasattr(node, 'symbol') and hasattr(node.symbol, 'type'):
        token_type = node.symbol.type
    # Check if it's a raw Token itself
    elif node and hasattr(node, 'type'):
        token_type = node.type
    return token_type == SimpleIRParser.NAME

# --- Instruction Analysis Helpers (Operating on StatementContext or ReturnStatementContext) ---

# <<< CORRECTED FUNCTION v3 >>>
def get_instruction_type_and_context(stmt_or_return_ctx):
    """
    Determines the instruction type string and returns the specific inner context
    (e.g., AssignContext, AllocStmtContext).
    Accepts StatementContext or ReturnStatementContext.
    Returns (instr_type_str, specific_instr_context) or (None, None).
    """
    # Handle ReturnStatementContext directly
    if isinstance(stmt_or_return_ctx, SimpleIRParser.ReturnStatementContext):
        return "return", stmt_or_return_ctx # Return the context itself

    # Check if it's a StatementContext
    if not isinstance(stmt_or_return_ctx, SimpleIRParser.StatementContext):
         logging.error(f"Expected StatementContext or ReturnStatementContext, got {type(stmt_or_return_ctx)}")
         return None, None

    ctx = stmt_or_return_ctx # It's a StatementContext

    # For labeled alternatives like 'assign # AssignInstr', the StatementContext (ctx)
    # should have a method named after the *inner rule* (assign) if that alternative was matched.
    # This method returns the context object for that inner rule (AssignContext).
    if hasattr(ctx, 'assign') and ctx.assign(): return "assign", ctx.assign()
    if hasattr(ctx, 'operation') and ctx.operation(): return "operation", ctx.operation()
    if hasattr(ctx, 'dereference') and ctx.dereference(): return "dereference", ctx.dereference()
    if hasattr(ctx, 'reference') and ctx.reference(): return "reference", ctx.reference()
    if hasattr(ctx, 'assignDereference') and ctx.assignDereference(): return "assign_dereference", ctx.assignDereference()
    if hasattr(ctx, 'call') and ctx.call(): return "call", ctx.call()
    if hasattr(ctx, 'label') and ctx.label(): return "label", ctx.label()
    if hasattr(ctx, 'gotoStatement') and ctx.gotoStatement(): return "goto", ctx.gotoStatement()
    if hasattr(ctx, 'ifGoto') and ctx.ifGoto(): return "ifgoto", ctx.ifGoto()
    if hasattr(ctx, 'allocStmt') and ctx.allocStmt(): return "alloc", ctx.allocStmt()
    if hasattr(ctx, 'addrStmt') and ctx.addrStmt(): return "addr", ctx.addrStmt()
    if hasattr(ctx, 'loadStmt') and ctx.loadStmt(): return "load", ctx.loadStmt()
    if hasattr(ctx, 'storeStmt') and ctx.storeStmt(): return "store", ctx.storeStmt()

    # If none of the above matched
    logging.warning(f"Could not determine specific instruction type for StatementContext: {get_instruction_text(ctx)}")
    return None, None


def get_defs(stmt_or_return_ctx):
    """Return the set of variables defined by the instruction."""
    defs = set()
    # Get the type string AND the specific inner context (e.g., AssignContext)
    instr_type, specific_ctx = get_instruction_type_and_context(stmt_or_return_ctx)
    if not specific_ctx:
        return defs # Warning already issued by previous call

    var_name = None
    try:
        # Operate on the specific_ctx now
        if instr_type in ["assign", "operation", "dereference", "reference", "call", "addr", "load"]:
            # Check if NAME method exists and returns a non-empty list/node at index 0
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                name_node_or_list = specific_ctx.NAME()
                target_node = None
                # NAME() can return a list or single node depending on grammar rule
                if isinstance(name_node_or_list, list):
                    if len(name_node_or_list) > 0:
                        target_node = name_node_or_list[0]
                elif isinstance(name_node_or_list, TerminalNode):
                     # This case likely applies if only one NAME exists (e.g., label, goto)
                     # but the check above restricts to instructions defining NAME(0)
                     pass # Should be handled by list check if NAME(0) exists

                if target_node: # Check if we found a node
                    var_name = safe_get_terminal_text(target_node)

        if var_name and var_name.isidentifier():
            defs.add(var_name)
    except Exception as e:
        logging.error(f"Error in get_defs for instruction '{get_instruction_text(stmt_or_return_ctx)}': {e}", exc_info=True)

    # logging.debug(f"Defs for '{get_instruction_text(stmt_or_return_ctx).strip()}': {defs}")
    return defs


def get_uses(stmt_or_return_ctx):
    """Return the set of variables used by the instruction."""
    uses = set()
    # Get the type string AND the specific inner context (e.g., AssignContext)
    instr_type, specific_ctx = get_instruction_type_and_context(stmt_or_return_ctx)
    if not specific_ctx:
        return uses

    try:
        # Operate on the specific_ctx now
        if instr_type == "assign":
            # assign: NAME ASSIGN operand=(NAME | NUM);
            if hasattr(specific_ctx, 'operand') and is_name_token(specific_ctx.operand):
                 uses.add(safe_get_operand_text(specific_ctx.operand))
        elif instr_type == "operation":
            # operation: NAME ASSIGN NAME operatorKind=(...) NAME;
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                name_nodes = specific_ctx.NAME() # [lhs, op1, op2]
                if isinstance(name_nodes, list) and len(name_nodes) > 2:
                    if name_nodes[1]: uses.add(safe_get_terminal_text(name_nodes[1])) # op1
                    if name_nodes[2]: uses.add(safe_get_terminal_text(name_nodes[2])) # op2
        elif instr_type == "dereference":
            # dereference: NAME ASSIGN STAR NAME;
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                 name_nodes = specific_ctx.NAME() # [lhs, addr_var]
                 if isinstance(name_nodes, list) and len(name_nodes) > 1 and name_nodes[1]:
                     uses.add(safe_get_terminal_text(name_nodes[1])) # address var
        elif instr_type == "reference":
            # reference: NAME ASSIGN AMPERSAND NAME;
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                 name_nodes = specific_ctx.NAME() # [lhs, var_ref]
                 if isinstance(name_nodes, list) and len(name_nodes) > 1 and name_nodes[1]:
                     uses.add(safe_get_terminal_text(name_nodes[1])) # var whose address is taken
        elif instr_type == "assign_dereference":
            # assignDereference: STAR NAME ASSIGN operand=(NAME | NUM);
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME) and specific_ctx.NAME():
                 uses.add(safe_get_terminal_text(specific_ctx.NAME())) # address var
            if hasattr(specific_ctx, 'operand') and is_name_token(specific_ctx.operand):
                 uses.add(safe_get_operand_text(specific_ctx.operand)) # value var if NAME
        elif instr_type == "call":
            # call: NAME ASSIGN CALL NAME NAME*;
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                 name_nodes = specific_ctx.NAME() # [lhs, func, arg1, arg2...]
                 num_names = len(name_nodes) if isinstance(name_nodes, list) else 0
                 for i in range(2, num_names): # Args start at index 2
                     arg_node = name_nodes[i]
                     if arg_node: uses.add(safe_get_terminal_text(arg_node))
        elif instr_type == "ifgoto":
            # ifGoto: IF operand1=(...) op=(...) operand2=(...) GOTO NAME;
            if hasattr(specific_ctx, 'operand1') and is_name_token(specific_ctx.operand1):
                uses.add(safe_get_operand_text(specific_ctx.operand1))
            if hasattr(specific_ctx, 'operand2') and is_name_token(specific_ctx.operand2):
                uses.add(safe_get_operand_text(specific_ctx.operand2))
        elif instr_type == "return":
            # returnStatement: RETURN operand=(NAME | NUM);
            if hasattr(specific_ctx, 'operand') and is_name_token(specific_ctx.operand):
                uses.add(safe_get_operand_text(specific_ctx.operand))
        # New array instructions
        elif instr_type == "addr":
             # addrStmt: NAME ASSIGN ADDR NAME COMMA NAME;
             if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                  name_nodes = specific_ctx.NAME() # [resultAddr, baseName, indexName]
                  if isinstance(name_nodes, list) and len(name_nodes) > 2:
                      # Base name might not be a 'use' in traditional dataflow, depends on semantics
                      # Index name definitely is a use
                      # if name_nodes[1]: uses.add(safe_get_terminal_text(name_nodes[1])) # baseName (Optional)
                      if name_nodes[2]: uses.add(safe_get_terminal_text(name_nodes[2])) # indexName
        elif instr_type == "load":
             # loadStmt: NAME ASSIGN LOAD NAME;
             if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                  name_nodes = specific_ctx.NAME() # [resultVal, addressName]
                  if isinstance(name_nodes, list) and len(name_nodes) > 1 and name_nodes[1]:
                      uses.add(safe_get_terminal_text(name_nodes[1])) # addressName
        elif instr_type == "store":
             # storeStmt: STORE NAME COMMA NAME;
             if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME):
                  name_nodes = specific_ctx.NAME() # [valueName, addressName]
                  if isinstance(name_nodes, list) and len(name_nodes) > 1:
                      if name_nodes[0]: uses.add(safe_get_terminal_text(name_nodes[0])) # valueName
                      if name_nodes[1]: uses.add(safe_get_terminal_text(name_nodes[1])) # addressName

    except Exception as e:
         logging.error(f"Error in get_uses for instruction '{get_instruction_text(stmt_or_return_ctx)}': {e}", exc_info=True)

    # Filter out None values and ensure they are valid identifiers
    final_uses = {u for u in uses if u and u.isidentifier()}
    # logging.debug(f"Uses for '{get_instruction_text(stmt_or_return_ctx).strip()}': {final_uses}")
    return final_uses


def has_side_effects(stmt_or_return_ctx):
    """Check if an instruction should *always* be kept by DCE."""
    instr_type, specific_ctx = get_instruction_type_and_context(stmt_or_return_ctx)
    if not instr_type: return True # Keep if type unknown

    return instr_type in [
        "call",
        "assign_dereference", # Modifies memory via pointer
        "return",
        "goto",
        "ifgoto",
        "label", # Needed as jump target
        "alloc", # Modifies memory allocation state
        "store"  # Modifies memory
        ]


def get_jump_target(stmt_or_return_ctx):
    """Get the target label from a goto or ifgoto instruction context."""
    instr_type, specific_ctx = get_instruction_type_and_context(stmt_or_return_ctx)
    if not specific_ctx: return None

    label_to_return = None
    try:
        if instr_type == "goto":
            # gotoStatement: GOTO NAME;
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME) and specific_ctx.NAME():
                 label_to_return = safe_get_terminal_text(specific_ctx.NAME())
        elif instr_type == "ifgoto":
            # ifGoto: IF operand1 op operand2 GOTO NAME;
            # Target label is the NAME node
            if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME) and specific_ctx.NAME():
                 label_node = specific_ctx.NAME()
                 if isinstance(label_node, TerminalNode):
                     label_to_return = safe_get_terminal_text(label_node)
                 elif isinstance(label_node, list): # Should not happen
                      logging.warning(f"ifGoto context unexpectedly returned list for NAME(): {get_instruction_text(stmt_or_return_ctx)}")
                      if len(label_node) > 0: label_to_return = safe_get_terminal_text(label_node[-1])

    except Exception as e:
        logging.error(f"Error getting jump target for '{get_instruction_text(stmt_or_return_ctx)}': {e}", exc_info=True)

    return label_to_return.strip() if label_to_return else None


def get_label(stmt_or_return_ctx):
    """Get the label defined by a label instruction context."""
    instr_type, specific_ctx = get_instruction_type_and_context(stmt_or_return_ctx)
    if not specific_ctx or instr_type != "label": return None

    label_text = None
    try:
        # label: NAME COLON;
        if hasattr(specific_ctx, 'NAME') and callable(specific_ctx.NAME) and specific_ctx.NAME():
             label_text = safe_get_terminal_text(specific_ctx.NAME())
    except Exception as e:
        logging.error(f"Error getting label for '{get_instruction_text(stmt_or_return_ctx)}': {e}", exc_info=True)

    return label_text.strip() if label_text else None


class IRList:
    """Helper class to collect instructions and metadata from the parse tree."""
    def __init__(self):
        self.instr_contexts = [] # List to hold StatementContext or ReturnStatementContext objects
        self.function_name = "unknown_function"
        self.locals_text = None # Store raw text for now
        self.params_text = None # Store raw text for now

    def collect_from_tree(self, tree):
        """Manually traverses the tree to collect info."""
        if not isinstance(tree, SimpleIRParser.UnitContext):
            logging.error("Tree root is not UnitContext.")
            return

        func_ctx = tree.function()
        if not func_ctx:
            logging.error("No FunctionContext found in UnitContext.")
            return

        # Get function name
        if func_ctx.functionName:
            self.function_name = func_ctx.functionName.text # Assigned token
            logging.debug(f"Captured function name: {self.function_name}")
        else:
            logging.warning("Could not find function name token in FunctionContext.")

        # Get locals text (if present)
        locals_ctx = func_ctx.localVariables()
        if locals_ctx:
            self.locals_text = get_instruction_text(locals_ctx).strip()
            logging.debug(f"Captured locals section text: {self.locals_text}")

        # Get parameters text (if present)
        params_ctx = func_ctx.parameters()
        if params_ctx:
             self.params_text = get_instruction_text(params_ctx).strip()
             logging.debug(f"Captured parameters section text: {self.params_text}")

        # Get statements
        stmts_ctx = func_ctx.statements()
        if stmts_ctx:
            # statement() returns a list of StatementContexts
            self.instr_contexts.extend(stmts_ctx.statement())
            logging.debug(f"Collected {len(stmts_ctx.statement())} statement contexts.")
        else:
            logging.warning("No statements context found in function.")

        # Get return statement (handle separately as it's not under 'statements')
        ret_ctx = func_ctx.returnStatement()
        if ret_ctx:
             # Add the ReturnStatementContext directly to the list
             self.instr_contexts.append(ret_ctx)
             logging.debug("Added return statement context.")


def build_cfg(instrs):
    """Takes a list of instruction contexts (StatementContext or ReturnStatementContext)
       and produces a CFG using NetworkX."""
    if nx is None:
        logging.error("NetworkX library is required to build the CFG.")
        return None, {}
    if not instrs:
        cfg = nx.DiGraph()
        cfg.add_node(-1, instrs=[], type='special', label='entry') # Entry node
        cfg.add_node(-2, instrs=[], type='special', label='exit')  # Exit node
        cfg.add_edge(-1, -2)
        return cfg, {}

    cfg = nx.DiGraph()
    entry_node = -1
    exit_node = -2
    cfg.add_node(entry_node, instrs=[], type='special', label='entry')
    cfg.add_node(exit_node, instrs=[], type='special', label='exit')

    leaders = {0}  # First instruction is always a leader
    label_map = {} # label_name -> instruction_index

    logging.debug("--- Identifying Leaders ---")
    for i, stmt_ctx in enumerate(instrs):
        instr_type, _ = get_instruction_type_and_context(stmt_ctx) # Use corrected helper
        if not instr_type:
            # Warning already issued by get_instruction_type_and_context
            logging.debug(f"Skipping leader identification for instruction {i} due to unknown type.")
            continue

        if instr_type == "label":
            label = get_label(stmt_ctx) # Pass outer context to helper
            if label:
                 if label in label_map:
                      logging.warning(f"Duplicate label '{label}' found at instruction {i}. Previous definition at {label_map[label]}.")
                 label_map[label] = i
                 leaders.add(i) # The label instruction itself is a leader

        elif instr_type in ["goto", "ifgoto"]:
            # Instruction FOLLOWING a jump is a leader
            follow_idx = i + 1
            if follow_idx < len(instrs):
                leaders.add(follow_idx)
            # Target of a jump is a leader (added below)

    logging.debug("--- Adding Jump Target Leaders ---")
    target_leaders_to_add = set()
    for i, stmt_ctx in enumerate(instrs):
         instr_type, _ = get_instruction_type_and_context(stmt_ctx)
         if not instr_type: continue

         if instr_type in ["goto", "ifgoto"]:
             target_label = get_jump_target(stmt_ctx) # Pass outer context
             if target_label and target_label in label_map:
                 target_instr_index = label_map[target_label]
                 target_leaders_to_add.add(target_instr_index)
             elif target_label:
                 logging.warning(f"Label '{target_label}' targeted by jump at instruction {i} ('{get_instruction_text(stmt_ctx).strip()}') not found in label_map.")

    leaders.update(target_leaders_to_add)

    # Ensure leaders are within bounds and unique
    sorted_leaders = sorted([l for l in leaders if l < len(instrs)])
    logging.debug(f"--- Sorted Leader Instruction Indices: {sorted_leaders} ---")

    # Map instruction index to basic block index
    instr_to_bb_map = {}
    bb_instrs = defaultdict(list) # bb_index -> list of instruction contexts
    current_bb_index = -1

    if not sorted_leaders: # Handle case of single block program (no jumps/labels)
        if instrs:
            logging.debug("No explicit leaders found, creating single block BB0.")
            current_bb_index = 0
            cfg.add_node(current_bb_index, type='code')
            for i, instr_ctx in enumerate(instrs):
                 bb_instrs[current_bb_index].append(instr_ctx)
                 instr_to_bb_map[i] = current_bb_index
    else:
        bb_leader_map = {leader_idx: bb_idx for bb_idx, leader_idx in enumerate(sorted_leaders)}
        logging.debug(f"--- Leader Index to BB Index Map: {bb_leader_map} ---")
        for i, instr_ctx in enumerate(instrs):
            if i in bb_leader_map:
                current_bb_index = bb_leader_map[i]
                # Add node to CFG when its leader is encountered
                if current_bb_index not in cfg: # Avoid adding node multiple times
                     cfg.add_node(current_bb_index, type='code')
                     logging.debug(f"  Starting BB{current_bb_index} at instruction {i}")

            if current_bb_index != -1: # Ensure we are inside a block
                 bb_instrs[current_bb_index].append(instr_ctx)
                 instr_to_bb_map[i] = current_bb_index
            else:
                 # This might happen if the first instruction isn't 0, though leader={0} should prevent this.
                 logging.error(f"Instruction {i} ('{get_instruction_text(instr_ctx).strip()}') does not belong to any basic block!")

    # Assign instructions to CFG nodes
    for bb_idx, instructions in bb_instrs.items():
        if bb_idx in cfg:
            cfg.nodes[bb_idx]['instrs'] = instructions
        else:
            logging.error(f"Basic block index {bb_idx} not found in CFG nodes during instruction assignment.")


    logging.debug("--- Adding Edges ---")
    # Connect entry node
    if 0 in instr_to_bb_map:
        first_bb_idx = instr_to_bb_map[0]
        logging.debug(f"  Adding edge: entry -> BB{first_bb_idx}")
        cfg.add_edge(entry_node, first_bb_idx)
    elif not instrs:
        logging.debug(f"  Adding edge: entry -> exit (empty program)")
        cfg.add_edge(entry_node, exit_node)
    else:
        logging.warning("No basic block found for instruction 0, cannot connect entry node.")

    # Connect basic blocks based on control flow
    for i, stmt_ctx in enumerate(instrs):
        if i not in instr_to_bb_map:
             logging.warning(f"Skipping edge creation for instruction {i}: Not mapped to a BB.")
             continue # Skip instructions not mapped to BBs

        current_bb_idx = instr_to_bb_map[i]
        instr_type, _ = get_instruction_type_and_context(stmt_ctx)
        if not instr_type: continue # Skip if type unknown

        # Check if it's the last instruction in its block
        is_last_in_block = (i + 1 == len(instrs) or (i + 1) in instr_to_bb_map and instr_to_bb_map[i+1] != current_bb_idx)

        if not is_last_in_block:
            continue # Edges are determined by the last instruction of a block

        logging.debug(f"  Processing edges for BB{current_bb_idx} ending at instr {i} ({instr_type})")

        added_successor = False
        if instr_type == "goto":
            target_label = get_jump_target(stmt_ctx) # Pass outer context
            target_bb_idx = exit_node # Default to exit
            if target_label and target_label in label_map:
                 target_instr_index = label_map[target_label]
                 if target_instr_index in instr_to_bb_map:
                     target_bb_idx = instr_to_bb_map[target_instr_index]
                 else:
                     logging.error(f"Goto target instruction index {target_instr_index} (Label '{target_label}') not mapped to a BB!")
            logging.debug(f"    Goto BB{current_bb_idx} -> BB{target_bb_idx} (Target: {target_label})")
            if current_bb_idx in cfg and target_bb_idx in cfg:
                 cfg.add_edge(current_bb_idx, target_bb_idx)
            added_successor = True

        elif instr_type == "ifgoto":
            # Conditional jump target
            target_label = get_jump_target(stmt_ctx) # Pass outer context
            target_bb_idx = exit_node # Default target is exit
            if target_label and target_label in label_map:
                target_instr_index = label_map[target_label]
                if target_instr_index in instr_to_bb_map:
                    target_bb_idx = instr_to_bb_map[target_instr_index]
                else:
                    logging.error(f"IfGoto target instruction index {target_instr_index} (Label '{target_label}') not mapped to a BB!")
            logging.debug(f"    IfGoto BB{current_bb_idx} -> BB{target_bb_idx} (Target: {target_label})")
            if current_bb_idx in cfg and target_bb_idx in cfg:
                 cfg.add_edge(current_bb_idx, target_bb_idx)

            # Fallthrough target
            fallthrough_instr_index = i + 1
            fallthrough_bb_idx = exit_node # Default fallthrough is exit
            if fallthrough_instr_index < len(instrs):
                 if fallthrough_instr_index in instr_to_bb_map:
                     fallthrough_bb_idx = instr_to_bb_map[fallthrough_instr_index]
                 else:
                     logging.warning(f"Fallthrough instruction index {fallthrough_instr_index} after 'if' in BB{current_bb_idx} not mapped to a BB! Defaulting edge to exit.")
            logging.debug(f"    IfGoto BB{current_bb_idx} -> BB{fallthrough_bb_idx} (Fallthrough)")
            if current_bb_idx in cfg and fallthrough_bb_idx in cfg:
                 cfg.add_edge(current_bb_idx, fallthrough_bb_idx)
            added_successor = True

        elif instr_type == "return":
            logging.debug(f"    Return BB{current_bb_idx} -> BB{exit_node}")
            if current_bb_idx in cfg and exit_node in cfg:
                 cfg.add_edge(current_bb_idx, exit_node)
            added_successor = True

        # If no explicit jump, connect to the next basic block sequentially
        if not added_successor:
            next_instr_index = i + 1
            if next_instr_index < len(instrs):
                if next_instr_index in instr_to_bb_map:
                    next_bb_idx = instr_to_bb_map[next_instr_index]
                    logging.debug(f"    Sequential BB{current_bb_idx} -> BB{next_bb_idx}")
                    if current_bb_idx in cfg and next_bb_idx in cfg:
                         cfg.add_edge(current_bb_idx, next_bb_idx)
                    added_successor = True
                else:
                    logging.warning(f"Sequential instruction index {next_instr_index} after BB{current_bb_idx} not mapped to a BB! Defaulting edge to exit.")
                    if current_bb_idx in cfg and exit_node in cfg:
                         cfg.add_edge(current_bb_idx, exit_node)
                    added_successor = True # Treat as connected to exit
            else:
                 # Last instruction of the program falls through to exit
                 logging.debug(f"    Sequential BB{current_bb_idx} -> BB{exit_node} (End of program)")
                 if current_bb_idx in cfg and exit_node in cfg:
                      cfg.add_edge(current_bb_idx, exit_node)
                 added_successor = True


    # Connect any dangling nodes (nodes without successors, excluding exit) to the exit node
    all_code_nodes = [n for n in cfg.nodes() if isinstance(n, int) and n >= 0]
    for node in all_code_nodes:
        if node in cfg and not list(cfg.successors(node)):
             logging.warning(f"Node BB{node} has no successors after edge creation. Connecting to BB{exit_node}.")
             if exit_node in cfg:
                  cfg.add_edge(node, exit_node)

    logging.debug("--- Finished Adding Edges ---")
    return cfg, label_map


def liveness_analysis(cfg):
    """Performs iterative liveness analysis on the CFG."""
    if nx is None or cfg is None: return None
    logging.info("Starting liveness analysis...")
    entry_node = -1
    exit_node = -2

    # Initialize live_in and live_out sets for all nodes
    for node in cfg.nodes:
        cfg.nodes[node]['live_in'] = set()
        cfg.nodes[node]['live_out'] = set()

    # Use a worklist approach
    worklist = deque(n for n in cfg.nodes if n != entry_node) # Start with all nodes except entry
    iteration = 0
    max_iterations = len(cfg.nodes) * 2 + 100 # Heuristic limit

    while worklist and iteration < max_iterations:
        node = worklist.popleft()
        iteration += 1

        if node == exit_node: continue  # Skip exit node calculation

        # Store old live_in to check for changes
        old_in = cfg.nodes[node]['live_in'].copy()

        # Calculate live_out[node] = union of live_in[successors]
        current_out = set()
        for succ in cfg.successors(node):
             current_out.update(cfg.nodes[succ].get('live_in', set()))

        # Calculate live_in[node] = use[node] union (live_out[node] - def[node])
        current_in_block = current_out.copy() # Start with live_out for the block
        instr_statements = cfg.nodes[node].get('instrs', [])

        for stmt_ctx in reversed(instr_statements):
             uses = get_uses(stmt_ctx) # Pass outer context
             defs = get_defs(stmt_ctx) # Pass outer context

             # Live_in before this instruction = uses U (Live_out_after - defs)
             current_in_block = uses.union(current_in_block - defs)

        # Update live sets for the node
        cfg.nodes[node]['live_in'] = current_in_block
        cfg.nodes[node]['live_out'] = current_out # Live_out was calculated before iterating block

        # If live_in changed, add predecessors to worklist
        if current_in_block != old_in:
            for pred in cfg.predecessors(node):
                 if pred not in worklist: # Avoid adding duplicates unnecessarily
                      worklist.append(pred)

    if iteration >= max_iterations:
         logging.warning(f"Liveness analysis did not converge after {max_iterations} iterations.")
    logging.info("Liveness analysis finished.")
    return cfg


def eliminate_dead_code(cfg):
    """Eliminates dead code based on liveness analysis results."""
    if nx is None or cfg is None: return None
    logging.info("Starting dead code elimination...")
    made_change_overall = False

    while True: # Keep iterating until no changes are made
        cfg = liveness_analysis(cfg)
        if cfg is None: return None # Stop if liveness failed
        logging.debug("Re-ran liveness analysis for DCE pass.")
        made_change_in_this_pass = False

        nodes_to_process = [n for n in list(cfg.nodes()) if isinstance(n, int) and n >= 0]

        for node in nodes_to_process:
            original_instrs = list(cfg.nodes[node].get('instrs', []))
            if not original_instrs: continue

            kept_instrs_for_node = []
            # Liveness flows backward, so analyze instructions backward
            live = cfg.nodes[node].get('live_out', set()).copy() # Live vars *after* the block

            for stmt_ctx in reversed(original_instrs):
                defs = get_defs(stmt_ctx) # Pass outer context
                uses = get_uses(stmt_ctx) # Pass outer context
                side_effects = has_side_effects(stmt_ctx) # Pass outer context

                # Keep instruction if it has side effects OR if any variable it defines is live *after* it
                keep_instruction = side_effects or any(d in live for d in defs)

                if keep_instruction:
                    kept_instrs_for_node.append(stmt_ctx)
                    # Update live set for the instruction *before* this one
                    live = uses.union(live - defs)
                else:
                    # Instruction is dead, mark change and don't add to kept list
                    logging.debug(f"  Node BB{node}: Eliminating dead instruction: {get_instruction_text(stmt_ctx).strip()}")
                    made_change_in_this_pass = True
                    made_change_overall = True # Mark that at least one change was made

            # Update the instructions in the CFG node if changes occurred
            final_kept_instrs = list(reversed(kept_instrs_for_node))
            if len(final_kept_instrs) != len(original_instrs):
                 cfg.nodes[node]['instrs'] = final_kept_instrs
                 eliminated_this_node = len(original_instrs) - len(final_kept_instrs)
                 logging.debug(f"  Node BB{node}: Updated instructions, eliminated {eliminated_this_node} in this pass.")

        if not made_change_in_this_pass:
             logging.info("  No changes made in this pass. DCE converged.")
             break # Exit the while loop if no changes were made
        else:
             logging.info("  Completed DCE pass, changes made. Rerunning Liveness and DCE.")


    # Final liveness run on the optimized code
    cfg = liveness_analysis(cfg)
    logging.info(f"Dead code elimination complete. Eliminated instructions: {made_change_overall}")

    return cfg


def print_optimized_ir(cfg, label_map, irl_data):
    """Prints the optimized SimpleIR in the standard format."""
    if nx is None or cfg is None:
        print("NetworkX not available or CFG is None, cannot print optimized IR.", file=sys.stderr)
        return

    print("\n--- Optimized SimpleIR ---")

    # Print header
    func_name = irl_data.function_name if irl_data.function_name else "unknown_function"
    print(f"function {func_name}")
    indent = "  "

    # Create reverse map: instruction index -> label name(s)
    idx_to_label = defaultdict(list)
    for label, idx in label_map.items():
        idx_to_label[idx].append(label)

    # Get original indices of instructions to print labels correctly
    original_indices = {}
    all_instrs_orig = []
    if hasattr(irl_data, 'instr_contexts'):
         all_instrs_orig = irl_data.instr_contexts
         original_indices = {id(instr): i for i, instr in enumerate(all_instrs_orig)}


    printed_instr_ids = set() # Avoid printing duplicates

    # Iterate through basic blocks in approximate original order
    bb_indices = sorted([node for node in cfg.nodes() if isinstance(node, int) and node >= 0])

    last_instr_ctx_printed = None # Track last non-label printed

    for bb_index in bb_indices:
        instrs_in_block = cfg.nodes[bb_index].get('instrs', [])
        if not instrs_in_block: continue # Skip empty blocks

        # Check if the first instruction of the block had a label originally
        first_instr_ctx = instrs_in_block[0]
        first_instr_id = id(first_instr_ctx)
        original_idx = original_indices.get(first_instr_id)

        printed_label_for_block = False
        if original_idx is not None and original_idx in idx_to_label:
            # Check if the first instruction *is* the label it points to
            first_instr_type, _ = get_instruction_type_and_context(first_instr_ctx)
            if first_instr_type == "label":
                 current_label = get_label(first_instr_ctx)
                 if current_label in idx_to_label[original_idx]:
                      print(f"{current_label}:") # Print label without indent
                      printed_label_for_block = True


        # Print instructions in the block
        for instr_ctx in instrs_in_block:
            instr_id = id(instr_ctx)
            if instr_id not in printed_instr_ids:
                 instr_type, _ = get_instruction_type_and_context(instr_ctx)

                 if instr_type == "label":
                      # Only print label if it wasn't the first instruction printed for the block
                      is_first = (instr_id == first_instr_id)
                      if not (is_first and printed_label_for_block):
                           current_label = get_label(instr_ctx)
                           if current_label:
                                print(f"{current_label}:")
                 elif instr_type == "return":
                      # Keep track of return statement but print it after loop
                      last_instr_ctx_printed = instr_ctx # Update last seen instruction
                      pass # Skip printing here
                 elif instr_type is not None: # Avoid printing if type was unknown
                      raw_text = get_instruction_text(instr_ctx).strip()
                      if raw_text:
                           print(f"{indent}{raw_text}")
                           last_instr_ctx_printed = instr_ctx # Update last seen instruction

                 printed_instr_ids.add(instr_id)


    # Print the return statement if the *last* instruction processed was 'return'
    # Or if it was the last instruction in the original list (basic assumption)
    final_return_ctx = None
    if last_instr_ctx_printed and isinstance(last_instr_ctx_printed, SimpleIRParser.ReturnStatementContext):
         final_return_ctx = last_instr_ctx_printed
    # Check original list only if nothing else was printed or last wasn't return
    elif not last_instr_ctx_printed or not isinstance(last_instr_ctx_printed, SimpleIRParser.ReturnStatementContext):
         last_orig_instr = all_instrs_orig[-1] if all_instrs_orig else None
         if last_orig_instr and isinstance(last_orig_instr, SimpleIRParser.ReturnStatementContext):
              # Check if this original return statement still exists in the optimized CFG
              found_in_cfg = False
              for node_idx in bb_indices:
                   if last_orig_instr in cfg.nodes[node_idx].get('instrs', []):
                        found_in_cfg = True
                        break
              if found_in_cfg:
                   final_return_ctx = last_orig_instr


    if final_return_ctx:
         return_text = get_instruction_text(final_return_ctx).strip()
         if return_text:
              print(f"{indent}{return_text}")


    # Print footer
    print(f"end function")


def visualize_graph(cfg, filename="graph.png"):
    """Visualize the CFG using pygraphviz, saving to the current directory."""
    if not GRAPHVIZ_AVAILABLE or not nx or not to_agraph:
        logging.debug("Skipping graph visualization (pygraphviz or networkx not available).")
        return
    if not cfg:
        logging.warning("Skipping graph visualization: CFG is None.")
        return

    filepath = filename
    logging.info(f"Attempting to save graph visualization to {filepath}")

    try:
        graph_copy = cfg.copy()
        A = to_agraph(graph_copy)
        A.graph_attr['rankdir'] = 'TD'
        A.node_attr['shape'] = 'box'
        A.node_attr['fontname'] = 'Courier New'

        for node in graph_copy.nodes:
            agraph_node = A.get_node(node)
            node_data = graph_copy.nodes[node]
            node_label_id = f"BB{node}" if isinstance(node, int) and node >=0 else str(node)
            label_parts = [node_label_id.replace(':', '\\:').replace('\n', '\\n')]

            if 'instrs' in node_data and node_data['instrs']:
                  instr_texts = [
                      get_instruction_text(instr).strip().replace('\n', '\\n').replace('{', '\\{').replace('}', '\\}').replace('<', '\\<').replace('>', '\\>')
                      for instr in node_data['instrs']
                  ]
                  label_parts.append("\\l".join(instr_texts) + "\\l")
            elif node_data.get('type') != 'special':
                  label_parts.append("(empty)\\l")

            if 'live_in' in node_data:
                  if node_data['live_in'] or node not in [-1, -2]:
                       live_in_str = ", ".join(sorted(list(node_data['live_in'])))
                       label_parts.append(f"IN: {{{live_in_str}}}\\l")
            if 'live_out' in node_data:
                  if node_data['live_out'] or node not in [-1, -2]:
                       live_out_str = ", ".join(sorted(list(node_data['live_out'])))
                       label_parts.append(f"OUT: {{{live_out_str}}}\\l")

            agraph_node.attr['label'] = "".join(label_parts)

        A.layout(prog="dot")
        A.draw(filepath)
        logging.info(f"CFG visualization saved successfully to {filepath}")

    except Exception as e:
        logging.warning(f"Could not visualize CFG to {filepath} (is graphviz installed and in PATH?): {e}", exc_info=True)


def textualize_graph(cfg):
    """Generate a textual representation of the CFG."""
    if nx is None or cfg is None: return "NetworkX not available or CFG is None."

    text = "Control Flow Graph\n"
    entry_node = -1
    exit_node = -2
    try:
        sorted_nodes = sorted(cfg.nodes, key=lambda x: (not isinstance(x, int), x))
    except TypeError:
        sorted_nodes = list(cfg.nodes)

    for node in sorted_nodes:
        node_data = cfg.nodes[node]
        node_label_id = f"BB{node}" if isinstance(node, int) and node >=0 else str(node)
        text += f'--- {node_label_id} ---\n'
        if 'instrs' in node_data and node_data['instrs']:
            text += "\n".join([f"  {get_instruction_text(instr).strip()}" for instr in node_data["instrs"]])
            text += "\n"
        elif node_data.get('type') != 'special':
             text += "  (empty)\n"

        successors = list(cfg.successors(node))
        successor_labels = [f"BB{s}" if isinstance(s, int) and s >=0 else str(s) for s in successors]

        if successor_labels:
            text += f'Successors: {", ".join(successor_labels)}\n'
        else:
            text += "Successors: (None)\n"

        if node not in [entry_node, exit_node]:
            if 'live_in' in node_data:
                 text += f"Live IN : {sorted(list(node_data['live_in']))}\n"
            if 'live_out' in node_data:
                 text += f"Live OUT: {sorted(list(node_data['live_out']))}\n"

        text += "\n"
    return text


# --- Main Execution ---

if __name__ == "__main__":
    if nx is None:
         print("Error: networkx library is required. Please install it (`pip install networkx`).", file=sys.stderr)
         sys.exit(1)

    logging.info("Reading SimpleIR input from stdin...")
    input_stream = StdinStream()

    output_dir = "."
    if not os.path.isdir(output_dir):
         logging.warning(f"Output directory '{output_dir}' not found. Saving graphs to current directory.")
         output_dir = "."

    logging.info(f"Output PNG files will be saved in: {os.path.abspath(output_dir)}")

    tree = None
    parser = None
    try:
        lexer = SimpleIRLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = SimpleIRParser(stream)
        parser.removeErrorListeners()
        error_listener = SyntaxErrListener()
        parser.addErrorListener(error_listener)
        tree = parser.unit()

        if error_listener.error_count > 0:
            print(f"Syntax errors found in SimpleIR input from stdin:", file=sys.stderr)
            for msg in error_listener.error_messages:
                 print(f"- {msg}", file=sys.stderr)
            exit(1)

    except Exception as e:
        print(f"Error during parsing SimpleIR from stdin: {e}", file=sys.stderr)
        import traceback
        logging.debug(traceback.format_exc())
        exit(1)


    # Collect instructions using the helper class
    irl_data = IRList()
    irl_data.collect_from_tree(tree)

    if not irl_data.instr_contexts:
        print(f"No instructions found in input from stdin.", file=sys.stderr)
        print("\n--- Optimized SimpleIR ---")
        print(f"function {irl_data.function_name}")
        print(f"end function")
        exit(0)

    try:
        # Build CFG
        cfg, label_map = build_cfg(irl_data.instr_contexts)
        if cfg is None: exit(1)
        logging.info("Control flow graph constructed.")
        print(textualize_graph(cfg))
        visualize_graph(cfg, os.path.join(output_dir, "cfg_initial.png"))

        # Liveness Analysis
        cfg_live = liveness_analysis(cfg)
        if cfg_live is None: exit(1)
        logging.info("Liveness analysis performed.")
        print(textualize_graph(cfg_live))
        visualize_graph(cfg_live, os.path.join(output_dir, "cfg_liveness.png"))

        # Dead Code Elimination
        cfg_optimized = eliminate_dead_code(cfg_live)
        if cfg_optimized is None: exit(1)
        logging.info("Dead code elimination performed.")
        print(textualize_graph(cfg_optimized))
        visualize_graph(cfg_optimized, os.path.join(output_dir, "cfg_optimized.png"))

        # Print final optimized IR
        print_optimized_ir(cfg_optimized, label_map, irl_data)

    except Exception as e:
        print(f"Error during optimization/output: {e}", file=sys.stderr)
        import traceback
        logging.error(traceback.format_exc())
        exit(1)

    logging.info(f"Processing finished successfully.")
    exit(0) # Explicitly exit with 0 on success
