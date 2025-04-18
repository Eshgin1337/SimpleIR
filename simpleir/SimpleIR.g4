grammar SimpleIR;


unit: function;

function: FUNCTION functionName=NAME localVariables? parameters? statements returnStatement end;

localVariables: LOCAL NAME (COMMA NAME)*; // Removed variables= label
parameters: PARAMETERS NAME+;       // Removed formals= label
statements: statement*;
returnStatement: RETURN operand=(NAME | NUM);
end: END FUNCTION; // Use tokens

// Statement rule with labels for all alternatives
statement
    : assign                # AssignInstr
    | dereference           # DereferenceInstr
    | reference             # ReferenceInstr
    | assignDereference     # AssignDereferenceInstr
    | operation             # OperationInstr
    | call                  # CallInstr
    | label                 # LabelInstr
    | gotoStatement         # GotoInstr
    | ifGoto                # IfGotoInstr
    | allocStmt             # AllocInstr  // NEW
    | addrStmt              # AddrInstr   // NEW
    | loadStmt              # LoadInstr   // NEW
    | storeStmt             # StoreInstr  // NEW
    ;

// Existing instruction rules (using Token names)
operation: NAME ASSIGN NAME operatorKind=(PLUS | MINUS | STAR | SLASH | PERCENT) NAME;
assign: NAME ASSIGN operand=(NAME | NUM);
dereference: NAME ASSIGN STAR NAME;
reference: NAME ASSIGN AMPERSAND NAME; // Using & token now
assignDereference: STAR NAME ASSIGN operand=(NAME | NUM);
call: NAME ASSIGN CALL NAME NAME*; // result := call func args*
label: NAME COLON;
gotoStatement: GOTO NAME;
ifGoto: IF operand1=(NAME | NUM) operatorKind=(EQ | NEQ | LT | LTE | GT | GTE) operand2=(NAME | NUM) GOTO NAME;

// New rules for array operations
allocStmt : ALLOC NAME COMMA NUM ;                 // alloc arrayName, sizeInElements
addrStmt  : NAME ASSIGN ADDR NAME COMMA NAME ;     // resultAddr := addr baseName, indexNameOrTemp
loadStmt  : NAME ASSIGN LOAD NAME ;                // resultVal := load addressNameOrTemp
storeStmt : STORE NAME COMMA NAME ;                // store valueNameOrTemp, addressNameOrTemp

FUNCTION : 'function';
LOCAL : 'local';
PARAMETERS : 'parameters';
RETURN : 'return';
END : 'end';
CALL : 'call';
GOTO : 'goto';
IF : 'if';
ALLOC : 'alloc'; // NEW
ADDR  : 'addr';  // NEW
LOAD  : 'load';  // NEW
STORE : 'store'; // NEW

// Use NAME for variables, temps (_t...), labels, function names
NAME: [a-zA-Z_] ([a-zA-Z_] | [0-9])* ; // Generic identifier MUST BE AFTER keywords
NUM: [0-9]+ ;                         // Integer literal

// Operators / Symbols
ASSIGN   : ':=' ;
LPAREN   : '(' ; // Retained if needed elsewhere, not used above
RPAREN   : ')' ; // Retained if needed elsewhere, not used above
LBRACKET : '[' ; // Retained if needed elsewhere, not used above
RBRACKET : ']' ; // Retained if needed elsewhere, not used above
SEMI     : ';' ; // Retained if needed elsewhere, not used above
COMMA    : ',' ; // Needed for new instructions
AMPERSAND: '&' ; // For reference operator
STAR     : '*' ; // For dereference ops AND mult op
COLON    : ':' ; // For labels

PLUS     : '+' ;
MINUS    : '-' ;
// STAR used for MULT
SLASH    : '/' ;
PERCENT  : '%' ;

EQ       : '=' ;
NEQ      : '!=' ;
LT       : '<' ;
LTE      : '<=' ;
GT       : '>' ;
GTE      : '>=' ;

// Whitespace - Discarded by the lexer
WS      : [ \t\r\n]+ -> skip ;
// Comments - Discarded by the lexer
COMMENT : '#' ~[\r\n]* -> skip ;