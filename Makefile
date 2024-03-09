SRC = main
EXAMPLES = $(wildcard examples/*/app.py)
EXAMPLES += $(wildcard examples/*/templates/*.html)
EXAMPLES += $(wildcard examples/*/*.toml)

default: $(SRC).pdf

%.pdf: %.tex $(EXAMPLES)
	pdflatex -shell-escape $<
	rm -f $(basename $<).aux $(basename $<).nav $(basename $<).out $(basename $<).snm $(basename $<).toc $(basename $<).log $(basename $<).vrb
	rm -r _minted-$(basename $<)

clean:
	rm -f $(SRC).pdf $(SRC).aux $(SRC).log $(SRC).bbl $(SRC).blg $(SRC).nav $(SRC).out $(SRC).snm $(SRC).toc

git_%:
	git add .
	git commit -m "$*"
	git push