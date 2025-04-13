grammar While;

// Top-level statement rule
s   : assignment # AssignmentStmt // <<<--- ADDED LABEL HERE
    | 'skip' # Skip
    | 'begin' s (';' s)* 'end' # Compound
    | 'if' b 'then' s 'else' s # If
    | 'while' b 'do' s # While
    ;

// Assignment rule now has two alternatives
assignment
    : ID ':=' a # SimpleAssignment        // Existing: x := 1
    | ID '[' a ']' ':=' a # ArrayElementAssignment // New: arr[i] := 5
    ;

// Boolean expressions
b   : 'true' # True
    | 'false' # False
    | 'not' b # Not
    | b 'and' b # And
    | b 'or' b # Or
    | a op=('<' | '<=' | '=' | '>' | '>=') a # ROp
    | '(' b ')' # BParen
    ;

// Arithmetic expressions (with precedence)
a   : a op=('+' | '-') a_term # AOpAddSub       // Lower precedence
    | a_term                 # ATerm
    ;

a_term
    : a_term op=('*' | '/') a_factor # AOpMulDiv // Higher precedence
    | a_factor                       # AFactor
    ;

a_factor // Highest precedence
    : ID # Var
    | NUM # Num
    | ID '[' a ']' # ArrayAccess      // Array access allowed here
    | '(' a ')' # AParen
    ;

// --- LEXER RULES ---

// Basic Tokens
ID  : [a-zA-Z] ([a-zA-Z] | [0-9])* ;
NUM : [0-9]+ ;

// Operators / Symbols
LBRACKET : '[' ;
RBRACKET : ']' ;
SEMI     : ';' ;
ASSIGN   : ':=' ; // Define assignment explicitly
LPAREN   : '(' ;
RPAREN   : ')' ;

// These keywords are implicitly defined by the literals in the parser rules
// but defining them can sometimes help avoid ambiguity or allow different casing.
// TRUE: 'true' ;
// FALSE: 'false' ;
// AND: 'and' ;
// OR: 'or' ;
// NOT: 'not' ;
// SKIP: 'skip';
// BEGIN: 'begin';
// END: 'end';
// IF: 'if';
// THEN: 'then';
// ELSE: 'else';
// WHILE: 'while';
// DO: 'do';

// Relational operators (implicitly defined)
// EQ    : '=' ;
// LT    : '<' ;
// LE    : '<=' ;
// GT    : '>' ;
// GE    : '>=' ;

// Arithmetic operators (implicitly defined)
// PLUS: '+' ;
// MINUS: '-' ;
// MULT: '*' ;
// DIV: '/' ;


// Whitespace and Comments
WS  : [ \t\n\r]+ -> skip ;
// SL_COMMENT:  '//' .*? '\n' -> skip ;