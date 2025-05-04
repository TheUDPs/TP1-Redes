# Makefile to compile informe.org into a PDF using Emacs

# Target file (output PDF)
TARGET = informe.pdf

# Source file (input Org file)
SOURCE = informe.org

# Emacs command to export Org to PDF
EMACS = emacs
EMACSFLAGS = --batch -Q --script scripts/export-to-pdf.el $(SOURCE)

# Default target
all: $(TARGET)

# Rule to generate PDF
$(TARGET): $(SOURCE)
	@echo "Compiling $< to PDF..."
	@$(EMACS) $(EMACSFLAGS) || (echo "Compilation failed"; exit 1)

# New target to execute all Org Babel blocks (e.g. generate images)
execute-code-blocks:
	$(EMACS) --batch -l scripts/process-org.el

# Clean up generated files
clean:
	rm -f $(TARGET)

# Phony targets
.PHONY: all clean execute-code-blocks
