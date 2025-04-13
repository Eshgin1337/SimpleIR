grammar While;

s:   ID ':=' a # Assignment
   | 'skip' # Skip
   // | s ';' s # Sequence
   | 'begin' s (';' s)* 'end' # Compound
   | 'if' b 'then' s 'else' s # If
   | 'while' b 'do' s # While
   ;

b:   'true' # True
   | 'false' # False
   | 'not' b # Not
   | b 'and' b # And
   | b 'or' b # Or
   | a op=('<' | '<=' | '=' | '>' | '>=') a # ROp
   | '(' b ')' # BParen
   ;

// Refactored 'a' rules for operator precedence and array access
a : a op=('+' | '-') a   # AOpAddSub
  | a_term               # ATerm
  ;

a_term
  : a_term op=('*' | '/') a_term # AOpMulDiv
  | a_factor                     # AFactor
  ;

a_factor
  : ID         # Var
  | NUM        # Num
  | ID '[' a ']' # ArrayAccess
  | '(' a ')'  # AParen
  ;


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
