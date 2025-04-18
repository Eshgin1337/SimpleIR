# Generated from SimpleIR.g4 by ANTLR 4.9.1
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .SimpleIRParser import SimpleIRParser
else:
    from SimpleIRParser import SimpleIRParser

# This class defines a complete listener for a parse tree produced by SimpleIRParser.
class SimpleIRListener(ParseTreeListener):

    # Enter a parse tree produced by SimpleIRParser#unit.
    def enterUnit(self, ctx:SimpleIRParser.UnitContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#unit.
    def exitUnit(self, ctx:SimpleIRParser.UnitContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#function.
    def enterFunction(self, ctx:SimpleIRParser.FunctionContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#function.
    def exitFunction(self, ctx:SimpleIRParser.FunctionContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#localVariables.
    def enterLocalVariables(self, ctx:SimpleIRParser.LocalVariablesContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#localVariables.
    def exitLocalVariables(self, ctx:SimpleIRParser.LocalVariablesContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#parameters.
    def enterParameters(self, ctx:SimpleIRParser.ParametersContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#parameters.
    def exitParameters(self, ctx:SimpleIRParser.ParametersContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#statements.
    def enterStatements(self, ctx:SimpleIRParser.StatementsContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#statements.
    def exitStatements(self, ctx:SimpleIRParser.StatementsContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#returnStatement.
    def enterReturnStatement(self, ctx:SimpleIRParser.ReturnStatementContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#returnStatement.
    def exitReturnStatement(self, ctx:SimpleIRParser.ReturnStatementContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#end.
    def enterEnd(self, ctx:SimpleIRParser.EndContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#end.
    def exitEnd(self, ctx:SimpleIRParser.EndContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#AssignInstr.
    def enterAssignInstr(self, ctx:SimpleIRParser.AssignInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#AssignInstr.
    def exitAssignInstr(self, ctx:SimpleIRParser.AssignInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#DereferenceInstr.
    def enterDereferenceInstr(self, ctx:SimpleIRParser.DereferenceInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#DereferenceInstr.
    def exitDereferenceInstr(self, ctx:SimpleIRParser.DereferenceInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#ReferenceInstr.
    def enterReferenceInstr(self, ctx:SimpleIRParser.ReferenceInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#ReferenceInstr.
    def exitReferenceInstr(self, ctx:SimpleIRParser.ReferenceInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#AssignDereferenceInstr.
    def enterAssignDereferenceInstr(self, ctx:SimpleIRParser.AssignDereferenceInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#AssignDereferenceInstr.
    def exitAssignDereferenceInstr(self, ctx:SimpleIRParser.AssignDereferenceInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#OperationInstr.
    def enterOperationInstr(self, ctx:SimpleIRParser.OperationInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#OperationInstr.
    def exitOperationInstr(self, ctx:SimpleIRParser.OperationInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#CallInstr.
    def enterCallInstr(self, ctx:SimpleIRParser.CallInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#CallInstr.
    def exitCallInstr(self, ctx:SimpleIRParser.CallInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#LabelInstr.
    def enterLabelInstr(self, ctx:SimpleIRParser.LabelInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#LabelInstr.
    def exitLabelInstr(self, ctx:SimpleIRParser.LabelInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#GotoInstr.
    def enterGotoInstr(self, ctx:SimpleIRParser.GotoInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#GotoInstr.
    def exitGotoInstr(self, ctx:SimpleIRParser.GotoInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#IfGotoInstr.
    def enterIfGotoInstr(self, ctx:SimpleIRParser.IfGotoInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#IfGotoInstr.
    def exitIfGotoInstr(self, ctx:SimpleIRParser.IfGotoInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#AllocInstr.
    def enterAllocInstr(self, ctx:SimpleIRParser.AllocInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#AllocInstr.
    def exitAllocInstr(self, ctx:SimpleIRParser.AllocInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#AddrInstr.
    def enterAddrInstr(self, ctx:SimpleIRParser.AddrInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#AddrInstr.
    def exitAddrInstr(self, ctx:SimpleIRParser.AddrInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#LoadInstr.
    def enterLoadInstr(self, ctx:SimpleIRParser.LoadInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#LoadInstr.
    def exitLoadInstr(self, ctx:SimpleIRParser.LoadInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#StoreInstr.
    def enterStoreInstr(self, ctx:SimpleIRParser.StoreInstrContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#StoreInstr.
    def exitStoreInstr(self, ctx:SimpleIRParser.StoreInstrContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#operation.
    def enterOperation(self, ctx:SimpleIRParser.OperationContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#operation.
    def exitOperation(self, ctx:SimpleIRParser.OperationContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#assign.
    def enterAssign(self, ctx:SimpleIRParser.AssignContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#assign.
    def exitAssign(self, ctx:SimpleIRParser.AssignContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#dereference.
    def enterDereference(self, ctx:SimpleIRParser.DereferenceContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#dereference.
    def exitDereference(self, ctx:SimpleIRParser.DereferenceContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#reference.
    def enterReference(self, ctx:SimpleIRParser.ReferenceContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#reference.
    def exitReference(self, ctx:SimpleIRParser.ReferenceContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#assignDereference.
    def enterAssignDereference(self, ctx:SimpleIRParser.AssignDereferenceContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#assignDereference.
    def exitAssignDereference(self, ctx:SimpleIRParser.AssignDereferenceContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#call.
    def enterCall(self, ctx:SimpleIRParser.CallContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#call.
    def exitCall(self, ctx:SimpleIRParser.CallContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#label.
    def enterLabel(self, ctx:SimpleIRParser.LabelContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#label.
    def exitLabel(self, ctx:SimpleIRParser.LabelContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#gotoStatement.
    def enterGotoStatement(self, ctx:SimpleIRParser.GotoStatementContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#gotoStatement.
    def exitGotoStatement(self, ctx:SimpleIRParser.GotoStatementContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#ifGoto.
    def enterIfGoto(self, ctx:SimpleIRParser.IfGotoContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#ifGoto.
    def exitIfGoto(self, ctx:SimpleIRParser.IfGotoContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#allocStmt.
    def enterAllocStmt(self, ctx:SimpleIRParser.AllocStmtContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#allocStmt.
    def exitAllocStmt(self, ctx:SimpleIRParser.AllocStmtContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#addrStmt.
    def enterAddrStmt(self, ctx:SimpleIRParser.AddrStmtContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#addrStmt.
    def exitAddrStmt(self, ctx:SimpleIRParser.AddrStmtContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#loadStmt.
    def enterLoadStmt(self, ctx:SimpleIRParser.LoadStmtContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#loadStmt.
    def exitLoadStmt(self, ctx:SimpleIRParser.LoadStmtContext):
        pass


    # Enter a parse tree produced by SimpleIRParser#storeStmt.
    def enterStoreStmt(self, ctx:SimpleIRParser.StoreStmtContext):
        pass

    # Exit a parse tree produced by SimpleIRParser#storeStmt.
    def exitStoreStmt(self, ctx:SimpleIRParser.StoreStmtContext):
        pass



del SimpleIRParser