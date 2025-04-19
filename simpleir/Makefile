GRAMMAR = SimpleIR

ANTLR_JAR = ../grammar/antlr-4.9.1-complete.jar
ANTLR_CMD = java -jar $(ANTLR_JAR)

all: $(GRAMMAR)Parser.py $(GRAMMAR)Listener.py

$(GRAMMAR)Parser.py $(GRAMMAR)Listener.py: $(GRAMMAR).g4 $(ANTLR_JAR)
	$(ANTLR_CMD) -Dlanguage=Python3 -visitor -listener $< -o .

clean:
	rm -f $(GRAMMAR).interp $(GRAMMAR)Lexer.interp $(GRAMMAR)Lexer.tokens $(GRAMMAR).tokens
	rm -f $(GRAMMAR)Lexer.py $(GRAMMAR)Parser.py $(GRAMMAR)Listener.py $(GRAMMAR)Visitor.py
	rm -f *.pyc `
	rm -rf __pycache__ 

.PHONY: all clean
