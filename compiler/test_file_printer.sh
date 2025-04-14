# Replace path/to/your/test/directory with the actual path
TEST_DIR="../tests/interpreter_tests"

echo "--- START OF TEST FILES ---"
for file in "$TEST_DIR"/*; do
  # Check if it is a file (and not a directory)
  if [ -f "$file" ]; then
    echo "" # Add a blank line separator
    echo "========================================"
    echo ">>> File: $file"
    echo "========================================"
    cat "$file"
  fi
done
echo ""
echo "--- END OF TEST FILES ---"
