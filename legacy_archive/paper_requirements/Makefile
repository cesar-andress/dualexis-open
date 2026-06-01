.PHONY: all pdf executive clean check

MAIN := main.tex
EXEC := executive_brief.tex
PDF  := main.pdf
EXEC_PDF := executive_brief.pdf

LATEXMK := $(shell command -v latexmk 2>/dev/null)
PDFLATEX := $(shell command -v pdflatex 2>/dev/null)
BIBTEX := $(shell command -v bibtex 2>/dev/null)

all: pdf executive

pdf: $(PDF)

executive: $(EXEC_PDF)

check:
	@test -f $(MAIN) || (echo "Missing $(MAIN)" && exit 1)
	@test -f $(EXEC) || (echo "Missing $(EXEC)" && exit 1)
	@test -f sections/document_control_macros.tex || exit 1
	@test -f sections/privacy_dpia_compliance.tex || exit 1
	@test -f sections/appendix_hardware_bom.tex || exit 1
	@echo "Requirements structure check passed."

ifeq ($(LATEXMK),)
ifeq ($(PDFLATEX),)
$(PDF) $(EXEC_PDF):
	@echo "Install latexmk or pdflatex."
	@exit 1
else
define BUILD_TEX
	$(PDFLATEX) -interaction=nonstopmode $(1)
ifneq ($(BIBTEX),)
	-$(BIBTEX) $(basename $(1))
endif
	$(PDFLATEX) -interaction=nonstopmode $(1)
	$(PDFLATEX) -interaction=nonstopmode $(1)
endef

$(PDF): $(MAIN) references.bib sections/*.tex figures/*.tex
	$(call BUILD_TEX,$(MAIN))

$(EXEC_PDF): $(EXEC) sections/*.tex figures/*.tex
	$(PDFLATEX) -interaction=nonstopmode $(EXEC)
	$(PDFLATEX) -interaction=nonstopmode $(EXEC)
endif
else
$(PDF): $(MAIN) references.bib
	$(LATEXMK) -pdf -interaction=nonstopmode $(MAIN)

$(EXEC_PDF): $(EXEC)
	$(LATEXMK) -pdf -interaction=nonstopmode $(EXEC)
endif

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc $(PDF) $(EXEC_PDF)
ifeq ($(LATEXMK),)
	@true
else
	-$(LATEXMK) -c 2>/dev/null || true
endif
