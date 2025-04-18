# Generated from SimpleIR.g4 by ANTLR 4.9.1
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .SimpleIRParser import SimpleIRParser
else:
    from SimpleIRParser import SimpleIRParser

# This class defines a complete generic visitor for a parse tree produced by SimpleIRParser.

class SimpleIRVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SimpleIRParser#unit.
    def visitUnit(self, ctx:SimpleIRParser.UnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#function.
    def visitFunction(self, ctx:SimpleIRParser.FunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#localVariables.
    def visitLocalVariables(self, ctx:SimpleIRParser.LocalVariablesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#parameters.
    def visitParameters(self, ctx:SimpleIRParser.ParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#statements.
    def visitStatements(self, ctx:SimpleIRParser.StatementsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#returnStatement.
    def visitReturnStatement(self, ctx:SimpleIRParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#end.
    def visitEnd(self, ctx:SimpleIRParser.EndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#AssignInstr.
    def visitAssignInstr(self, ctx:SimpleIRParser.AssignInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#DereferenceInstr.
    def visitDereferenceInstr(self, ctx:SimpleIRParser.DereferenceInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#ReferenceInstr.
    def visitReferenceInstr(self, ctx:SimpleIRParser.ReferenceInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#AssignDereferenceInstr.
    def visitAssignDereferenceInstr(self, ctx:SimpleIRParser.AssignDereferenceInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#OperationInstr.
    def visitOperationInstr(self, ctx:SimpleIRParser.OperationInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#CallInstr.
    def visitCallInstr(self, ctx:SimpleIRParser.CallInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#LabelInstr.
    def visitLabelInstr(self, ctx:SimpleIRParser.LabelInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#GotoInstr.
    def visitGotoInstr(self, ctx:SimpleIRParser.GotoInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#IfGotoInstr.
    def visitIfGotoInstr(self, ctx:SimpleIRParser.IfGotoInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#AllocInstr.
    def visitAllocInstr(self, ctx:SimpleIRParser.AllocInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#AddrInstr.
    def visitAddrInstr(self, ctx:SimpleIRParser.AddrInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#LoadInstr.
    def visitLoadInstr(self, ctx:SimpleIRParser.LoadInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#StoreInstr.
    def visitStoreInstr(self, ctx:SimpleIRParser.StoreInstrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#operation.
    def visitOperation(self, ctx:SimpleIRParser.OperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#assign.
    def visitAssign(self, ctx:SimpleIRParser.AssignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#dereference.
    def visitDereference(self, ctx:SimpleIRParser.DereferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#reference.
    def visitReference(self, ctx:SimpleIRParser.ReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#assignDereference.
    def visitAssignDereference(self, ctx:SimpleIRParser.AssignDereferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#call.
    def visitCall(self, ctx:SimpleIRParser.CallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#label.
    def visitLabel(self, ctx:SimpleIRParser.LabelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#gotoStatement.
    def visitGotoStatement(self, ctx:SimpleIRParser.GotoStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#ifGoto.
    def visitIfGoto(self, ctx:SimpleIRParser.IfGotoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#allocStmt.
    def visitAllocStmt(self, ctx:SimpleIRParser.AllocStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#addrStmt.
    def visitAddrStmt(self, ctx:SimpleIRParser.AddrStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#loadStmt.
    def visitLoadStmt(self, ctx:SimpleIRParser.LoadStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleIRParser#storeStmt.
    def visitStoreStmt(self, ctx:SimpleIRParser.StoreStmtContext):
        return self.visitChildren(ctx)



del SimpleIRParser