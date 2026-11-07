# OpenResty Primer - project convenience targets
# Documentation lives in doc/ (Sphinx + MyST, bilingual en/zh_CN) and is
# published to GitHub Pages via the gh-pages branch.

DOC_DIR ?= doc

.PHONY: help deps build publish serve serve-en clean

help:
	@echo "OpenResty Primer - available targets:"
	@echo "  deps     Install python documentation dependencies (uv sync)"
	@echo "  build    Build the Sphinx site (en + zh_CN) into $(DOC_DIR)/_build/site/"
	@echo "  publish  Build and publish the built HTML to GitHub Pages (gh-pages)"
	@echo "  serve    Build and serve the full bilingual site at http://127.0.0.1:8000/"
	@echo "  serve-en Build and serve the English site at http://127.0.0.1:8000/"
	@echo "  clean    Remove the Sphinx build output"

deps:
	$(MAKE) -C $(DOC_DIR) deps

build:
	$(MAKE) -C $(DOC_DIR) build

publish:
	$(MAKE) -C $(DOC_DIR) publish

serve:
	$(MAKE) -C $(DOC_DIR) serve-all

serve-en:
	$(MAKE) -C $(DOC_DIR) serve

clean:
	$(MAKE) -C $(DOC_DIR) clean
