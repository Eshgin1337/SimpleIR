GRAMMAR = SimpleIR

all: $(GRAMMAR)Parser.py

$(GRAMMAR)Parser.py: $(GRAMMAR).g4
	antlr4 -Dlanguage=Python3 -visitor $<

clean:
	rm -f $(GRAMMAR).interp $(GRAMMAR)Lexer.interp $(GRAMMAR)Lexer.tokens $(GRAMMAR).tokens
	rm -f $(GRAMMAR)Lexer.py $(GRAMMAR)Parser.py $(GRAMMAR)Listener.py $(GRAMMAR)Visitor.py

clobber: clean
	rm -f $(ANTLR)
