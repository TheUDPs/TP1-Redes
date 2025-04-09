# Makefile to compile informe.org into a PDF using Emacs

# Target file (output PDF)
TARGET = informe.pdf

# Source file (input Org file)
SOURCE = informe.org

# Emacs command to export Org to PDF
EMACS = emacs
EMACSFLAGS = --batch -Q --eval '(load-library "org")' --visit=$(SOURCE) --funcall org-latex-export-to-pdf

# Default target
all: $(TARGET)

# Rule to generate the PDF from the Org file
$(TARGET): $(SOURCE)
	$(EMACS) $(EMACSFLAGS)

# Clean up generated files
clean:
	rm -f $(TARGET)

# Phony targets
.PHONY: all clean
