import os
import sys
sys.path.append('./')
sys.path.append('../') 
import itertools
from collections import defaultdict, deque 
from antlr4 import *
from simpleir.SimpleIRLexer import SimpleIRLexer
from simpleir.SimpleIRParser import SimpleIRParser
from simpleir.SimpleIRListener import SimpleIRListener
import logging
logging.basicConfig(level=logging.INFO) 
import networkx as nx
import pygraphviz # this is for visualization with dot layout
from networkx.drawing.nx_agraph import to_agraph


def get_instruction_text(ctx):
    """Gets the raw text of an instruction context."""
    return ctx.start.getInputStream().getText(ctx.start.start, ctx.stop.stop)

def get_instruction_type(ctx):
    """Determine the type of instruction from context."""
    if isinstance(ctx, SimpleIRParser.AssignContext):
        return "assign"
    elif isinstance(ctx, SimpleIRParser.OperationContext): 
        return "operation"
    elif isinstance(ctx, SimpleIRParser.DereferenceContext):
        return "dereference" 
    elif isinstance(ctx, SimpleIRParser.ReferenceContext):
        return "reference" 
    elif isinstance(ctx, SimpleIRParser.AssignDereferenceContext):
        return "assign_dereference" 
    elif isinstance(ctx, SimpleIRParser.CallContext):
        return "call"
    elif isinstance(ctx, SimpleIRParser.LabelContext):
        return "label"
    elif isinstance(ctx, SimpleIRParser.GotoStatementContext):
        return "goto"
    elif isinstance(ctx, SimpleIRParser.IfGotoContext):
        return "ifgoto"
    elif isinstance(ctx, SimpleIRParser.ReturnStatementContext):
        return "return"
    else:
        if hasattr(ctx, 'op'):
             return "operation" 
        return "unknown"


def get_defs(ctx):
    """Return the set of variables defined by the instruction context."""
    defs = set()
    instr_type = get_instruction_type(ctx)

    if instr_type in ["assign", "operation", "dereference", "reference"]:
         if ctx.getChildCount() > 1 and ctx.getChild(1).getText() == ':=':
             var_name = ctx.getChild(0).getText()
             if var_name and (var_name[0].isalpha() or var_name[0] == '_'):
                  defs.add(var_name)

    elif instr_type == "call":
         if ctx.getChildCount() > 1 and ctx.getChild(1).getText() == ':=':
             var_name = ctx.getChild(0).getText()
             if var_name and (var_name[0].isalpha() or var_name[0] == '_'):
                  defs.add(var_name)

    return defs


def get_uses(ctx):
    uses = set()
    instr_type = get_instruction_type(ctx)

    if instr_type == "assign":
        if ctx.getChildCount() >= 3 and ctx.getChild(1).getText() == ':=':
             uses.add(ctx.getChild(2).getText())
    elif instr_type == "operation":
        if ctx.getChildCount() >= 3 and ctx.getChild(1).getText() == ':=':
            if ctx.getChildCount() == 5: 
                uses.add(ctx.getChild(2).getText())
                uses.add(ctx.getChild(4).getText())
            elif ctx.getChildCount() == 4: 
                uses.add(ctx.getChild(3).getText())
            elif ctx.getChildCount() == 3: 
                uses.add(ctx.getChild(2).getText())
    elif instr_type == "dereference":
         if ctx.getChildCount() >= 4 and ctx.getChild(1).getText() == ':=':
            uses.add(ctx.getChild(3).getText())
    elif instr_type == "reference":
         if ctx.getChildCount() >= 4 and ctx.getChild(1).getText() == ':=':
            uses.add(ctx.getChild(3).getText())
    elif instr_type == "assign_dereference":
        if ctx.getChildCount() >= 4 and ctx.getChild(2).getText() == ':=':
             uses.add(ctx.getChild(1).getText())
             uses.add(ctx.getChild(3).getText())
    elif instr_type == "call":
        start_index = 4 
        for i in range(start_index, ctx.getChildCount()):
            arg_ctx = ctx.getChild(i)
            try:
                if isinstance(arg_ctx.getPayload(), Token) and arg_ctx.getPayload().type == SimpleIRParser.NAME:
                    uses.add(arg_ctx.getText())
            except AttributeError:
                 arg_text = arg_ctx.getText()
                 if arg_text and (arg_text[0].isalpha() or arg_text[0] == '_'): uses.add(arg_text)
    elif instr_type == "ifgoto":
        if ctx.getChildCount() >= 4:
            op1_ctx = ctx.getChild(1)
            op2_ctx = ctx.getChild(3)
            try:
                if isinstance(op1_ctx.getPayload(), Token) and op1_ctx.getPayload().type == SimpleIRParser.NAME:
                     uses.add(op1_ctx.getText())
                if isinstance(op2_ctx.getPayload(), Token) and op2_ctx.getPayload().type == SimpleIRParser.NAME:
                     uses.add(op2_ctx.getText())
            except AttributeError: 
                 op1_text = op1_ctx.getText()
                 op2_text = op2_ctx.getText()
                 if op1_text and (op1_text[0].isalpha() or op1_text[0] == '_'): uses.add(op1_text)
                 if op2_text and (op2_text[0].isalpha() or op2_text[0] == '_'): uses.add(op2_text)
    elif instr_type == "return":
        if ctx.getChildCount() >= 2:
            uses.add(ctx.getChild(1).getText())

    final_uses = set()
    for u in uses:
        u_stripped = u.strip()
        if u_stripped and (u_stripped[0].isalpha() or u_stripped[0] == '_'):
             final_uses.add(u_stripped)

    return final_uses

def has_side_effects(ctx):
    """Check if an instruction should *always* be kept by DCE."""
    instr_type = get_instruction_type(ctx)
    return instr_type in [
        "call",                 
        "assign_dereference",   
        "return",               
        "goto",                 
        "ifgoto",               
        "label"                 
        ]


def get_jump_target(ctx):
    """Get the target label from a goto or ifgoto instruction."""
    instr_type = get_instruction_type(ctx)
    label_to_return = None
    if instr_type == "goto":
        if ctx.getChildCount() >= 2:
            label_to_return = ctx.getChild(1).getText().strip() 
    elif instr_type == "ifgoto":
        EXPECTED_LABEL_INDEX = 5 
        if ctx.getChildCount() > EXPECTED_LABEL_INDEX:
             potential_label = ctx.getChild(EXPECTED_LABEL_INDEX).getText().strip() 
             if potential_label and (potential_label[0].isalpha() or potential_label[0] == '_'):
                  label_to_return = potential_label
             else:
                  logging.warning(f"Child {EXPECTED_LABEL_INDEX} of IfGoto is '{potential_label}', doesn't look like label: {get_instruction_text(ctx)}")
        else:
             logging.warning(f"IfGoto has only {ctx.getChildCount()} children, expected at least {EXPECTED_LABEL_INDEX+1} for label at index {EXPECTED_LABEL_INDEX}: {get_instruction_text(ctx)}")

    return label_to_return


def controlflow(instrs):
    """Takes a list of SimpleIR instruction contexts and produces a CFG."""
    if not instrs:
        cfg = nx.DiGraph()
        cfg.add_node('entry', instrs=[], type='special')
        cfg.add_node('exit', instrs=[], type='special')
        cfg.add_edge('entry', 'exit')
        return cfg, {}

    leaders = {0}  
    label_map = {} 

    logging.debug("--- Identifying Leaders ---")
    for i, instr_ctx in enumerate(instrs):
        instr_type = get_instruction_type(instr_ctx)

        if instr_type == "label":
            label = get_label(instr_ctx)
            if label:
                 label_map[label] = i
                 leaders.add(i) 

        elif instr_type in ["goto", "ifgoto"]:
            follow_idx = i + 1
            if follow_idx < len(instrs):
                leaders.add(follow_idx)

    logging.debug("--- Adding Jump Target Leaders ---")
    target_leaders_to_add = set()
    for i, instr_ctx in enumerate(instrs):
         instr_type = get_instruction_type(instr_ctx)
         if instr_type in ["goto", "ifgoto"]:
             target_label = get_jump_target(instr_ctx) 
             if target_label and target_label in label_map:
                 target_instr_index = label_map[target_label]
                 target_leaders_to_add.add(target_instr_index)
             elif target_label:
                 logging.warning(f"Label '{target_label}' targeted by jump at instruction {i} not found in label_map.")

    leaders.update(target_leaders_to_add)

    sorted_leaders = sorted(list(leaders))
    sorted_leaders = [l for l in sorted_leaders if l <= len(instrs)] 
    logging.debug(f"--- Sorted Leader Instruction Indices: {sorted_leaders} ---")

    leader_to_bb_idx = {leader_instr_idx: i for i, leader_instr_idx in enumerate(sorted_leaders)}
    logging.debug(f"--- Leader Index to BB Index Map: {leader_to_bb_idx} ---")

    bb_instrs = defaultdict(list)
    if not sorted_leaders:
         if instrs: 
              leader_to_bb_idx[0] = 0
              sorted_leaders = [0]
              bb_instrs[0].extend(instrs)
              logging.warning("No explicit leaders found, treating program as single block.")
    else:
        for i in range(len(sorted_leaders)):
            start_leader_instr_idx = sorted_leaders[i]
            if start_leader_instr_idx >= len(instrs):
                continue

            end_instr_idx = sorted_leaders[i+1] if i + 1 < len(sorted_leaders) else len(instrs)
            bb_index = leader_to_bb_idx[start_leader_instr_idx]

            logging.debug(f"  Creating BB{bb_index} from instructions {start_leader_instr_idx} to {end_instr_idx-1}")
            for instr_idx in range(start_leader_instr_idx, end_instr_idx):
                 if instr_idx < len(instrs):
                      bb_instrs[bb_index].append(instrs[instr_idx])
                 else: 
                      logging.error(f"Instr index {instr_idx} out of bounds (len={len(instrs)}) building BB{bb_index}.")

    cfg = nx.DiGraph()
    entry_node_id = -1 
    exit_node_id = -2
    cfg.add_node(entry_node_id, instrs=[], type='special')
    cfg.add_node(exit_node_id, instrs=[], type='special')

    active_bb_indices = set(bb_instrs.keys())

    for bb_index in leader_to_bb_idx.values(): 
        instrs_in_block = bb_instrs.get(bb_index, []) 
        cfg.add_node(bb_index, instrs=instrs_in_block, type='code')


    logging.debug("--- Adding Edges ---")
    first_bb_idx = leader_to_bb_idx.get(0)
    if first_bb_idx is not None:
        logging.debug(f"  Adding edge: BB{entry_node_id} -> BB{first_bb_idx}")
        cfg.add_edge(entry_node_id, first_bb_idx)
    elif not instrs:
        logging.debug(f"  Adding edge: BB{entry_node_id} -> BB{exit_node_id} (empty program)")
        cfg.add_edge(entry_node_id, exit_node_id)
    else:
        logging.warning("No leader found for instruction 0, cannot connect entry node.")

    for bb_index in active_bb_indices: 
        instrs_in_block = bb_instrs[bb_index] 
        last_instr_ctx = instrs_in_block[-1]
        last_instr_type = get_instruction_type(last_instr_ctx)

        try:
            current_leader_instr_idx = -1
            for l_idx, bb_i in leader_to_bb_idx.items():
                 if bb_i == bb_index:
                     current_leader_instr_idx = l_idx
                     break
            if current_leader_instr_idx == -1: raise ValueError("Leader not found")
            last_instr_index = current_leader_instr_idx + len(instrs_in_block) - 1

        except ValueError:
             logging.error(f"Could not determine leader index/last instruction index for BB{bb_index}. Skipping edge creation.")
             continue

        logging.debug(f"  Processing edges for BB{bb_index} (instrs {current_leader_instr_idx}..{last_instr_index}) ending with {last_instr_type}")

        added_successor = False 

        if last_instr_type == "goto":
            target_label = get_jump_target(last_instr_ctx)
            target_bb_idx = exit_node_id # Default to exit
            if target_label and target_label in label_map:
                 target_leader_instr_index = label_map[target_label]
                 if target_leader_instr_index in leader_to_bb_idx:
                     target_bb_idx = leader_to_bb_idx[target_leader_instr_index]
                 else:
                     logging.error(f"Goto target leader index {target_leader_instr_index} (Label '{target_label}') not in leader map!")
            logging.debug(f"    Goto BB{bb_index} -> BB{target_bb_idx} (Target: {target_label})")
            cfg.add_edge(bb_index, target_bb_idx)
            added_successor = True

        elif last_instr_type == "ifgoto":
            target_label = get_jump_target(last_instr_ctx)
            target_bb_idx = exit_node_id # Default target is exit
            if target_label and target_label in label_map:
                target_leader_instr_index = label_map[target_label]
                if target_leader_instr_index in leader_to_bb_idx:
                    target_bb_idx = leader_to_bb_idx[target_leader_instr_index]
                else:
                    logging.error(f"IfGoto target leader index {target_leader_instr_index} (Label '{target_label}') not in leader map!")
            logging.debug(f"    IfGoto BB{bb_index} -> BB{target_bb_idx} (Target: {target_label})")
            cfg.add_edge(bb_index, target_bb_idx)

            fallthrough_leader_instr_index = last_instr_index + 1
            fallthrough_bb_idx = exit_node_id # Default fallthrough is exit
            if fallthrough_leader_instr_index < len(instrs):
                 if fallthrough_leader_instr_index in leader_to_bb_idx:
                     fallthrough_bb_idx = leader_to_bb_idx[fallthrough_leader_instr_index]
                 else:
                     logging.error(f"Fallthrough instruction index {fallthrough_leader_instr_index} after 'if' in BB{bb_index} was not found in leader map! CFG incorrect.")
            logging.debug(f"    IfGoto BB{bb_index} -> BB{fallthrough_bb_idx} (Fallthrough)")
            cfg.add_edge(bb_index, fallthrough_bb_idx)
            added_successor = True 

        elif last_instr_type == "return":
            logging.debug(f"    Return BB{bb_index} -> BB{exit_node_id}")
            cfg.add_edge(bb_index, exit_node_id)
            added_successor = True

        if not added_successor:
            current_leader_instr_idx = -1
            for l_idx, bb_i in leader_to_bb_idx.items():
                 if bb_i == bb_index:
                     current_leader_instr_idx = l_idx
                     break

            if current_leader_instr_idx != -1:
                 try:
                     current_block_pos = sorted_leaders.index(current_leader_instr_idx)
                     if current_block_pos + 1 < len(sorted_leaders):
                         next_leader_instr_index = sorted_leaders[current_block_pos + 1]
                         if next_leader_instr_index == last_instr_index + 1:
                             next_bb_idx = leader_to_bb_idx[next_leader_instr_index]
                             logging.debug(f"    Sequential BB{bb_index} -> BB{next_bb_idx}")
                             cfg.add_edge(bb_index, next_bb_idx)
                             added_successor = True

                 except ValueError:
                     logging.error(f"Could not find current leader index {current_leader_instr_idx} in sorted list for BB{bb_index}.")

            if not added_successor:
                 logging.debug(f"    Sequential BB{bb_index} -> BB{exit_node_id} (End of sequence or fallback)")
                 cfg.add_edge(bb_index, exit_node_id)


    all_code_nodes = [n for n in cfg.nodes() if isinstance(n, int) and n >= 0]
    for node in all_code_nodes:
        if node in active_bb_indices and not list(cfg.successors(node)):
             logging.warning(f"Node BB{node} has no successors after edge creation. Connecting to BB{exit_node_id}.")
             cfg.add_edge(node, exit_node_id)

    logging.debug("--- Finished Adding Edges ---")
    return cfg, label_map

def get_label(ctx):
    """Get the label defined by a label instruction."""
    instr_type = get_instruction_type(ctx)
    if instr_type == "label":
        if ctx.getChildCount() >= 1:
             label_text = ctx.getChild(0).getText().strip() # Strip whitespace first
             if label_text.endswith(':'):
                  label_clean = label_text[:-1].strip() # Strip again after removing colon
                  return label_clean
             else:
                  return label_text # Already stripped
    return None


class IRList(SimpleIRListener):
    def __init__(self):
        self.instr = [] 
        self.function_name = None


    def enterFunction(self, ctx: SimpleIRParser.FunctionContext):
        if ctx.functionName: # checking if the labeled token exists
            self.function_name = ctx.functionName.text
            logging.debug(f"Captured function name: {self.function_name}")
        else:
            logging.warning("Could not find function name token in FunctionContext.")
            self.function_name = "unknown_function"
    
    def enterLocalVariables(self, ctx: SimpleIRParser.LocalVariablesContext):
         self.locals_text = ctx.start.getInputStream().getText(ctx.start.start, ctx.stop.stop).strip()
         logging.debug(f"Captured locals section text.")

    def enterParameters(self, ctx: SimpleIRParser.ParametersContext):
         self.params_text = ctx.start.getInputStream().getText(ctx.start.start, ctx.stop.stop).strip()
         logging.debug(f"Captured parameters section text.")

    def _add_instr(self, ctx):
        if isinstance(ctx, (SimpleIRParser.AssignContext, SimpleIRParser.OperationContext,
                             SimpleIRParser.DereferenceContext, SimpleIRParser.ReferenceContext,
                             SimpleIRParser.AssignDereferenceContext, SimpleIRParser.CallContext,
                             SimpleIRParser.LabelContext, SimpleIRParser.GotoStatementContext,
                             SimpleIRParser.IfGotoContext, SimpleIRParser.ReturnStatementContext)):
            self.instr.append(ctx) 
    def enterOperation(self, ctx:SimpleIRParser.OperationContext):
        self._add_instr(ctx)

    def enterAssign(self, ctx:SimpleIRParser.AssignContext):
        self._add_instr(ctx)

    def enterDereference(self, ctx:SimpleIRParser.DereferenceContext):
        self._add_instr(ctx)

    def enterReference(self, ctx:SimpleIRParser.ReferenceContext):
        self._add_instr(ctx)

    def enterAssignDereference(self, ctx:SimpleIRParser.AssignDereferenceContext):
        self._add_instr(ctx)

    def enterCall(self, ctx:SimpleIRParser.CallContext):
        self._add_instr(ctx)

    def enterLabel(self, ctx:SimpleIRParser.LabelContext):
        self._add_instr(ctx)

    def enterGotoStatement(self, ctx:SimpleIRParser.GotoStatementContext):
        self._add_instr(ctx)

    def enterIfGoto(self, ctx:SimpleIRParser.IfGotoContext):
        self._add_instr(ctx)

    def enterReturnStatement(self, ctx:SimpleIRParser.ReturnStatementContext):
        self._add_instr(ctx)



def visualize_graph(cfg, filename="graph.png"): 
    """Visualize the CFG using pygraphviz, saving to the current directory."""
    filepath = filename
    logging.info(f"Attempting to save graph visualization to {filepath}")

    try:
        A = to_agraph(cfg)
        for node in cfg.nodes:
             node_label_id = f"BB{node}" if isinstance(node, int) else str(node)
             label = f"{node_label_id}\n"
             if 'instrs' in cfg.nodes[node] and cfg.nodes[node]['instrs']:
                  instr_texts = [get_instruction_text(instr).strip() for instr in cfg.nodes[node]['instrs']]
                  label += "\n".join(instr_texts)
             elif cfg.nodes[node].get('type') != 'special':
                  label += "(empty)"

             if 'live_in' in cfg.nodes[node]:
                  if cfg.nodes[node]['live_in'] or node not in [-1, -2]:
                       label += f"\nIN: {sorted(list(cfg.nodes[node]['live_in']))}"
             if 'live_out' in cfg.nodes[node]:
                  if cfg.nodes[node]['live_out'] or node not in [-1, -2]:
                       label += f"\nOUT: {sorted(list(cfg.nodes[node]['live_out']))}"

             graphviz_node = A.get_node(str(node))
             graphviz_node.attr['label'] = label
             graphviz_node.attr['shape'] = 'box'

        A.layout(prog="dot")
        A.draw(filepath) 
        logging.info(f"CFG visualization saved successfully to {filepath}")

    except Exception as e:
        import traceback
        logging.warning(f"Could not visualize CFG to {filepath} (is graphviz installed and in PATH?): {e}")

def textualize_graph(cfg):
    """Generate a textual representation of the CFG."""
    text = "Control Flow Graph\n"
    try:
        sorted_nodes = sorted(cfg.nodes)
    except TypeError: 
        sorted_nodes = list(cfg.nodes)

    for node in sorted_nodes:
        text += f'--- BB{node} ---\n'
        if 'instrs' in cfg.nodes[node] and cfg.nodes[node]['instrs']:
            text += "\n".join([get_instruction_text(instr) for instr in cfg.nodes[node]["instrs"]])
            text += "\n"
        else:
             text += "(empty)\n"

        successors = list(cfg.successors(node))
        if successors:
            text += f'Successors: {", ".join([f"BB{s}" for s in successors])}\n'
        else:
            text += "Successors: (None - Exit?)\n"

        if 'live_in' in cfg.nodes[node]:
             text += f"Live IN : {sorted(list(cfg.nodes[node]['live_in']))}\n"
        if 'live_out' in cfg.nodes[node]:
             text += f"Live OUT: {sorted(list(cfg.nodes[node]['live_out']))}\n"

        text += "\n"
    return text


def controlflow(instrs):
    """Takes a list of SimpleIR instruction contexts and produces a CFG."""
    if not instrs:
        cfg = nx.DiGraph()
        cfg.add_node('entry', instrs=[])
        cfg.add_node('exit', instrs=[])
        cfg.add_edge('entry', 'exit')
        return cfg, {}

    leaders = {0}  
    label_map = {} 

    for i, instr_ctx in enumerate(instrs):
        instr_type = get_instruction_type(instr_ctx)
        if instr_type == "label":
            label = get_label(instr_ctx)
            if label:
                 label_map[label] = i
        elif instr_type in ["goto", "ifgoto"]:
            if i + 1 < len(instrs):
                leaders.add(i + 1)
            target_label = get_jump_target(instr_ctx)

    for i, instr_ctx in enumerate(instrs):
         instr_type = get_instruction_type(instr_ctx)
         if instr_type in ["goto", "ifgoto"]:
             target_label = get_jump_target(instr_ctx)
             if target_label in label_map:
                 leaders.add(label_map[target_label])
             else:
                 logging.warning(f"Label '{target_label}' not found for jump at instruction {i}")


    sorted_leaders = sorted(list(leaders))
    leader_map = {leader: i for i, leader in enumerate(sorted_leaders)} 

    bb_instrs = defaultdict(list)
    bb_map = {} 
    for i in range(len(sorted_leaders)):
        start_leader = sorted_leaders[i]
        end_leader = sorted_leaders[i+1] if i + 1 < len(sorted_leaders) else len(instrs)
        bb_index = leader_map[start_leader]

        for instr_idx in range(start_leader, end_leader):
             bb_instrs[bb_index].append(instrs[instr_idx])
             bb_map[instr_idx] = bb_index


    cfg = nx.DiGraph()
    entry_node = -1 
    exit_node = -2 
    cfg.add_node(entry_node, instrs=[])
    cfg.add_node(exit_node, instrs=[])


    for bb_index, instrs_in_block in bb_instrs.items():
        cfg.add_node(bb_index, instrs=instrs_in_block)

    if 0 in leader_map: 
         cfg.add_edge(entry_node, leader_map[0])
    elif not instrs: 
         cfg.add_edge(entry_node, exit_node)


    for bb_index, instrs_in_block in bb_instrs.items():
        if not instrs_in_block: 
             continue

        last_instr_ctx = instrs_in_block[-1]
        last_instr_type = get_instruction_type(last_instr_ctx)
        last_instr_index = instrs.index(last_instr_ctx) 

        if last_instr_type == "goto":
            target_label = get_jump_target(last_instr_ctx)
            if target_label in label_map:
                 target_instr_index = label_map[target_label]
                 target_bb_index = bb_map[target_instr_index]
                 cfg.add_edge(bb_index, target_bb_index)
            else: 
                 cfg.add_edge(bb_index, exit_node)
        elif last_instr_type == "ifgoto":
            target_label = get_jump_target(last_instr_ctx)
            if target_label in label_map:
                 target_instr_index = label_map[target_label]
                 target_bb_index = bb_map[target_instr_index]
                 cfg.add_edge(bb_index, target_bb_index)
            else: 
                 cfg.add_edge(bb_index, exit_node)
            fallthrough_instr_index = last_instr_index + 1
            if fallthrough_instr_index < len(instrs):
                 fallthrough_bb_index = bb_map[fallthrough_instr_index]
                 cfg.add_edge(bb_index, fallthrough_bb_index)
            else: 
                 cfg.add_edge(bb_index, exit_node)

        elif last_instr_type == "return":
            cfg.add_edge(bb_index, exit_node)
        else:
            next_instr_index = last_instr_index + 1
            if next_instr_index < len(instrs):
                 if next_instr_index in bb_map:
                     next_bb_index = bb_map[next_instr_index]
                     if next_bb_index != bb_index: 
                         cfg.add_edge(bb_index, next_bb_index)
                     elif not list(cfg.successors(bb_index)):
                          cfg.add_edge(bb_index, exit_node)

            else: 
                cfg.add_edge(bb_index, exit_node)

    all_nodes = list(cfg.nodes())
    for node in all_nodes:
        if node != exit_node and not list(cfg.successors(node)):
            if node == entry_node and not list(cfg.successors(node)):
                if exit_node in cfg: 
                     cfg.add_edge(entry_node, exit_node)
            elif node != entry_node: 
                 logging.debug(f"Connecting dangling node BB{node} to exit.")
                 cfg.add_edge(node, exit_node)


    return cfg, label_map



def liveness_analysis(cfg):
    for node in cfg.nodes:
        cfg.nodes[node]['live_in'] = set()
        cfg.nodes[node]['live_out'] = set()

    worklist = deque(cfg.nodes())
    while worklist:
        node = worklist.popleft()
        if node == -2: continue  

        current_out = set()
        for succ in cfg.successors(node):
            current_out.update(cfg.nodes[succ]['live_in'])
        
        current_in = current_out.copy()
        instrs = cfg.nodes[node].get('instrs', [])
        
        for instr in reversed(instrs):
            uses = get_uses(instr)
            defs = get_defs(instr)
            
            if get_instruction_type(instr) == "return" and hasattr(instr, 'operand'):
                uses.add(instr.operand.text)
            
            current_in = uses.union(current_in - defs)

        if current_in != cfg.nodes[node]['live_in'] or current_out != cfg.nodes[node]['live_out']:
            cfg.nodes[node]['live_in'] = current_in
            cfg.nodes[node]['live_out'] = current_out
            worklist.extend(cfg.predecessors(node))
    
    return cfg


def eliminate_dead_code(cfg):
    """Eliminates dead code based on liveness analysis results."""
    logging.info("Starting dead code elimination...")
    total_eliminated_count = 0
    made_change_in_last_pass = True

    while made_change_in_last_pass: 
        cfg = liveness_analysis(cfg) 
        logging.debug("Re-ran liveness analysis for DCE pass.")
        made_change_in_this_pass = False 

        nodes_to_process = [n for n in list(cfg.nodes()) if isinstance(n, int) and n >= 0]

        for node in nodes_to_process:
            original_instrs = list(cfg.nodes[node].get('instrs', [])) 
            if not original_instrs: continue

            kept_instrs_for_node = [] 
            live = cfg.nodes[node]['live_out'].copy()
            node_changed_this_iteration = False 

            for instr in reversed(original_instrs):
                defs = get_defs(instr)
                uses = get_uses(instr)
                side_effects = has_side_effects(instr)

                keep_instruction = side_effects or any(d in live for d in defs)

                if keep_instruction:
                    kept_instrs_for_node.append(instr)
                    live = uses.union(live - defs)
                else:
                    logging.debug(f"  Node BB{node}: Eliminating: {get_instruction_text(instr).strip()}")
                    node_changed_this_iteration = True 

            if node_changed_this_iteration:
                final_kept_instrs = list(reversed(kept_instrs_for_node))
                if len(final_kept_instrs) != len(original_instrs):
                     cfg.nodes[node]['instrs'] = final_kept_instrs
                     made_change_in_this_pass = True 
                     eliminated_this_node = len(original_instrs) - len(final_kept_instrs)
                     logging.debug(f"  Node BB{node}: Updated instructions, eliminated {eliminated_this_node} this pass.")

        made_change_in_last_pass = made_change_in_this_pass
        if made_change_in_this_pass:
             current_total_instrs = sum(len(cfg.nodes[n].get('instrs',[])) for n in nodes_to_process)
             logging.info(f"  Completed DCE pass, changes made. Rerunning.")
        else:
             logging.info("  No changes made in this pass. DCE converged.")


    cfg = liveness_analysis(cfg)
    logging.info(f"Dead code elimination complete.") 

    return cfg


def print_optimized_ir(cfg, label_map, irl_data): 
    """Prints the optimized SimpleIR in the format: function NAME ... end function"""
    print("\n--- Optimized SimpleIR ---") 

    func_name = irl_data.function_name if irl_data.function_name else "unknown_function"
    print(f"function {func_name}")
    indent = "  " 

    bb_indices = sorted([node for node in cfg.nodes() if isinstance(node, int) and node >= 0])
    printed_instrs_ids = set() 

    for bb_index in bb_indices:
        instrs_in_block = cfg.nodes[bb_index].get('instrs', [])
        for instr_ctx in instrs_in_block:
            instr_id = id(instr_ctx)
            if instr_id not in printed_instrs_ids:
                 raw_text = get_instruction_text(instr_ctx).strip()
                 print(f"{indent}{raw_text}")
                 printed_instrs_ids.add(instr_id)

    print(f"end function")

if __name__ == "__main__":
    logging.info("Reading SimpleIR input from stdin...")
    input_stream = StdinStream()

    logging.info(f"Output PNG files will be saved in the current directory: {os.getcwd()}")

    try:
        lexer = SimpleIRLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = SimpleIRParser(stream)
        tree = parser.unit()

        if parser.getNumberOfSyntaxErrors() > 0:
            print(f"Syntax errors found in SimpleIR input from stdin.", file=sys.stderr)
            exit(1)
    except Exception as e:
        print(f"Error during parsing from stdin: {e}", file=sys.stderr)
        import traceback
        logging.debug(traceback.format_exc())
        exit(1)


    walker = ParseTreeWalker()
    irl = IRList()
    walker.walk(irl, tree)

    if not irl.instr:
        print(f"No instructions found in input from stdin.", file=sys.stderr)

    try:
        cfg, label_map = controlflow(irl.instr)
        logging.info("Control flow graph constructed.")
        print(textualize_graph(cfg))
        visualize_graph(cfg, "cfg_initial.png")

        cfg_live = liveness_analysis(cfg)
        logging.info("Liveness analysis performed.")
        print(textualize_graph(cfg_live))
        visualize_graph(cfg_live, "cfg_liveness.png")

        cfg_optimized = eliminate_dead_code(cfg_live)
        logging.info("Dead code elimination performed.")
        print(textualize_graph(cfg_optimized))
        visualize_graph(cfg_optimized, "cfg_optimized.png")

        print_optimized_ir(cfg_optimized, label_map, irl)

    except Exception as e:
        print(f"Error during optimization/output: {e}", file=sys.stderr)
        import traceback
        logging.debug(traceback.format_exc())
        exit(1)

    logging.info(f"Processing finished for input from stdin.")

