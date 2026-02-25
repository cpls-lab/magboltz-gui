TEXINPUTS=.:$(CURDIR)/cern-beamer//:
LATEX=pdflatex
LATEX_FLAGS=-interaction=nonstopmode -halt-on-error

TEX=magboltz_gui_presentation.tex
PDF=$(TEX:.tex=.pdf)

.DEFAULT_GOAL := build

.PHONY: build clean clean-keep-pdf

build:
	TEXINPUTS=$(TEXINPUTS) $(LATEX) $(LATEX_FLAGS) $(TEX)

$(PDF): $(TEX)
	TEXINPUTS=$(TEXINPUTS) $(LATEX) $(LATEX_FLAGS) $(TEX)

clean:
	rm -f $(PDF) *.aux *.log *.nav *.out *.snm *.toc *.vrb *.bbl *.blg

clean-keep-pdf:
	rm -f *.aux *.log *.nav *.out *.snm *.toc *.vrb *.bbl *.blg
