grammar While; // Combined Grammar: Declarations + Statements + Arrays

// ----- PARSER RULES -----

// Statement rule 's': can be a declaration or an executable command
s   : declaration # DeclarationStmt  // Declaration: int x; bool a[10];
    | assignment # AssignmentStmt    // Assignment: x := e; a[e] := e
    | skip_stmt # Skip             // Skip: skip
    | compound_stmt # Compound     // Block: begin s; s; ... s end
    | if_stmt # If                 // Conditional: if e then s else s
    | while_stmt # While           // Loop: while e do s
    ;

// Declaration rule (Handles int/bool, scalar/array)
declaration
    : typeName=(INT | BOOL) ID (LBRACKET size=NUM RBRACKET)? // Matches 'int x', 'bool y', 'int a[10]' etc.
    ;

// Assignment rule (uses assignTarget and unified expression 'e')
assignment
    : assignTarget ASSIGN e // Matches 'x := e' or 'a[e] := e'
    ;

// Target for assignment (variable or array element)
assignTarget
    : ID # AssignVarTarget           // Assign to variable 'x'
    | ID LBRACKET e RBRACKET # AssignArrayTarget // Assign to array element 'a[e]'
    ;

// Specific statement rules using token names
skip_stmt : K_SKIP ; // Use K_SKIP token

compound_stmt : BEGIN s (SEMI s)* END ; // Sequence of statements separated by SEMI

if_stmt : IF e THEN s ELSE s ; // Uses unified expression 'e' for condition

while_stmt : WHILE e DO s ; // Uses unified expression 'e', no 'done' keyword

// Unified Expression Hierarchy 'e' (Handles bool, comparisons, arithmetic with precedence)
e   : e op=(AND | OR) e # EBinOpAndOr         // Precedence 5 (Lowest)
    | compExpr          # EComp
    ;

compExpr
    : compExpr op=(LT | LE | EQ | GT | GE) compExpr # EBinOpComp // Precedence 4
    | addExpr                                        # EAdd
    ;

addExpr
    : addExpr op=(PLUS | MINUS) addExpr # EBinOpAddSub    // Precedence 3
    | multExpr                          # EMult
    ;

multExpr
    : multExpr op=(MULT | DIV) multExpr # EBinOpMulDiv    // Precedence 2
    | unaryExpr                         # EUnary
    ;

unaryExpr
    : NOT unaryExpr # ENot                // Precedence 1 (Highest operator)
    | primaryExpr   # EPrimary
    ;

primaryExpr // Atoms (Highest precedence)
    : TRUE # True                 // Boolean literal true
    | FALSE # False                // Boolean literal false
    | ID # Var                     // Simple variable reference
    | NUM # Num                    // Integer literal
    | ID LBRACKET e RBRACKET # ArrayAccess // Array element reference a[e]
    | LPAREN e RPAREN # Paren             // Parenthesized expression
    ;


// ----- LEXER RULES -----

// Keywords MUST come BEFORE the ID rule to be tokenized correctly
BEGIN   : 'begin';
END     : 'end';
IF      : 'if';
THEN    : 'then';
ELSE    : 'else';
WHILE   : 'while';
DO      : 'do';
K_SKIP  : 'skip'; // Renamed from SKIP to avoid conflict
TRUE    : 'true' ;
FALSE   : 'false' ;
AND     : 'and' ;
OR      : 'or' ;
NOT     : 'not' ;
INT     : 'int';
BOOL    : 'bool';

// Basic Tokens that are NOT keywords
ID  : [a-zA-Z] ([a-zA-Z] | [0-9])* ; // Generic ID MUST BE AFTER keywords
NUM : [0-9]+ ;                      // Integer literal

// Operators / Symbols
ASSIGN   : ':=' ;
LPAREN   : '(' ;
RPAREN   : ')' ;
LBRACKET : '[' ;
RBRACKET : ']' ;
SEMI     : ';' ;
EQ       : '=' ;
LT       : '<' ;
LE       : '<=' ;
GT       : '>' ;
GE       : '>=' ;
PLUS     : '+' ;
MINUS    : '-' ;
MULT     : '*' ;
DIV      : '/' ;

// Whitespace - Discarded by the lexer
WS  : [ \t\n\r]+ -> skip ;

// Optional: Single-line comments - Discarded by the lexer
// SL_COMMENT:  '//' .*? '\n' -> skip ;