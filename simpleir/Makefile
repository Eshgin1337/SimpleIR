GRAMMAR = SimpleIR

# --- Define JAR and Command (like in the other Makefile) ---
# Adjust path to JAR if it's not in ../grammar/ relative to simpleir/
# Ensure this version matches your Python runtime (e.g., 4.9.1)
ANTLR_JAR = ../grammar/antlr-4.9.1-complete.jar
# Define the command to run ANTLR via Java
ANTLR_CMD = java -jar $(ANTLR_JAR)

# --- Targets ---
# Target 'all' depends on generating the necessary Python files
# Interpreter.py uses Listener, so let's make sure that's generated too
all: $(GRAMMAR)Parser.py $(GRAMMAR)Listener.py

# Rule to generate SimpleIR parser, lexer, listener, visitor components
# Depends on the grammar file and the JAR file
# $< refers to the first prerequisite (SimpleIR.g4)
# Added -listener because your Interpreter.py uses it
# Added -o . to ensure output goes into the current (simpleir) directory
$(GRAMMAR)Parser.py $(GRAMMAR)Listener.py: $(GRAMMAR).g4 $(ANTLR_JAR)
	$(ANTLR_CMD) -Dlanguage=Python3 -visitor -listener $< -o .

# --- Clean Rule ---
# Updated clean rule
clean:
	rm -f $(GRAMMAR).interp $(GRAMMAR)Lexer.interp $(GRAMMAR)Lexer.tokens $(GRAMMAR).tokens
	rm -f $(GRAMMAR)Lexer.py $(GRAMMAR)Parser.py $(GRAMMAR)Listener.py $(GRAMMAR)Visitor.py
	rm -f *.pyc # Remove compiled python files if any
	rm -rf __pycache__ # Remove cache directory

# Declare non-file targets
.PHONY: all clean