grammar TypeWhile;

s  : assignTarget ':=' e # Assignment
   | 'skip' # Skip
   | 'begin' s (';' s)* 'end' # Compound
   | 'if' e 'then' s 'else' s # If
   | 'while' e 'do' s # While
   | typeName=('int' | 'bool') ID ('[' size=NUM ']')? # Declaration
   ;

assignTarget
  : ID             # AssignVarTarget
  | ID '[' e ']'   # AssignArrayTarget
  ;

e : e op=('and' | 'or') e    # EBinOpAndOr
  | compExpr                 # EComp
  ;

compExpr
  : compExpr op=('<' | '<=' | '=' | '>' | '>=') compExpr # EBinOpComp
  | addExpr                                            # EAdd
  ;

addExpr
  : addExpr op=('+' | '-') addExpr # EBinOpAddSub
  | multExpr                       # EMult
  ;

multExpr
  : multExpr op=('*' | '/') multExpr # EBinOpMulDiv
  | unaryExpr                        # EUnary
  ;

unaryExpr
  : 'not' unaryExpr # ENot
  | primaryExpr     # EPrimary
  ;

primaryExpr
  : 'true'         # True
  | 'false'        # False
  | ID             # Var
  | NUM            # Num
  | ID '[' e ']'   # ArrayAccess
  | '(' e ')'      # Paren
  ;


INT: 'int' ;
BOOL: 'bool' ;

TRUE: 'true' ;
FALSE: 'false' ;
AND: 'and' ;
OR: 'or' ;
NOT: 'not' ;

ID: [a-zA-Z] ([a-zA-Z] | [0-9])* ;
NUM: [0-9]+ ;

EQ: '=' ;
LT: '<' ;
LE: '<=' ;
GT: '>' ;
GE: '>=' ;

PLUS: '+' ;
MINUS: '-' ;
MULT: '*' ;
DIV: '/' ;

WS:  [ \t\n\r]+ -> skip ;
SL_COMMENT:  '//' .*? '\n' -> skip ;
