# Makefile for Sphinx documentation

UV              ?= uv
SPHINXOPTS      ?= -W --keep-going -n
SPHINXBUILD     ?= $(UV) run --locked sphinx-build
SPHINXAUTOBUILD ?= $(UV) run --locked sphinx-autobuild
PYTHON          ?= $(UV) run --locked python
SPHINXINTL      ?= $(UV) run --locked sphinx-intl
SOURCEDIR       = .
BUILDDIR        = _build
SITEDIR         ?= $(BUILDDIR)/site
DOCTREESDIR     ?= $(BUILDDIR)/doctrees
PORT            ?= 8000
PKB_SCRIPT_DIR  ?= scripts
PKB_REPO_ROOT   ?= ..
PKB_DOC_DIR     ?= .
PKB_ARGS        ?=
DEFAULT_LANG    ?= en
CONF_MIN_LEVEL  ?= L3
FUNCTION_SLUG   ?= openresty-doc
AGENTBOX_FUNC   ?= functions/$(FUNCTION_SLUG)
AGENTBOX_GEN    ?= $(PKB_SCRIPT_DIR)/gen_agentbox_files.py
# Use Homebrew node for abx on macOS to avoid Codex.app code-signing conflicts
BREW_NODE       ?= $(shell command -v /opt/homebrew/opt/node/bin/node 2>/dev/null || echo node)
ABX             ?= $(BREW_NODE) $(shell which abx 2>/dev/null || echo abx)
# GitHub Pages publishing
PAGES_BRANCH    ?= gh-pages
PAGES_DIR       ?= _gh-pages

.PHONY: help Makefile clean install deps build html html-en html-loose html-zh html-all gettext intl-update translate-zh compile-intl build-landing serve serve-live serve-all pkb-check pkb-check-i18n pkb-level1 pkb-review-status changelog-draft strip-confidential agentbox-init agentbox-gen agentbox-deploy publish publish-agentbox

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo ""
	@echo "Custom targets:"
	@echo "  deps               Install locked documentation dependencies with uv"
	@echo "  install            Alias for deps"
	@echo "  build              Clean, deterministic full bilingual build (en + zh_CN)"
	@echo "  publish            Build and publish $(SITEDIR) to GitHub Pages ($(PAGES_BRANCH))"
	@echo "  intl-update        Manual: regenerate .pot and merge into .po after English changes"
	@echo "                     (heavy - the ingested 08-lua-nginx-module page has ~2.4k msgids)"
	@echo "  html               Build strict English HTML into $(SITEDIR)/en/"
	@echo "  html-en            Build English HTML into $(SITEDIR)/en/"
	@echo "  html-loose         Build HTML without treating warnings as errors"
	@echo "  html-zh            Build Chinese HTML into $(SITEDIR)/zh/"
	@echo "  html-all           Build bilingual site into $(SITEDIR)/"
	@echo "  gettext            Generate .pot catalogs"
	@echo "  intl-update        Update zh_CN .po translation files"
	@echo "  translate-zh       Apply dictionary translations to .po files"
	@echo "  compile-intl       Compile zh_CN .mo files"
	@echo "  build-landing      Generate bilingual landing page at $(SITEDIR)/index.html"
	@echo "  serve              Build and preview English at http://127.0.0.1:$(PORT)/"
	@echo "  serve-live         Auto-reload dev server (English only)"
	@echo "  serve-all          Serve bilingual site at http://127.0.0.1:$(PORT)/"
	@echo "  pkb-check          Zero-token staleness check"
	@echo "  pkb-check-i18n     Check zh_CN translation sync"
	@echo "  pkb-level1         Apply Level 1 mechanical refreshes"
	@echo "  pkb-review-status  Human review dashboard (status, score, confidentiality)"
	@echo "  changelog-draft    Generate changelog draft into _generated/"
	@echo "  strip-confidential Remove pages at >= CONF_MIN_LEVEL (default L3) from $(SITEDIR)"
	@echo "  agentbox-init      Verify agentbox.yaml and scaffold function dir"
	@echo "  agentbox-gen       Build site + generate files.ts for AgentBox"
	@echo "  agentbox-deploy    Deploy to AgentBox edge function"
	@echo "  publish-agentbox   Build bilingual site, strip confidential pages, gen files.ts, and deploy to AgentBox"

install:
	$(UV) sync --locked

deps: install

clean:
	rm -rf "$(BUILDDIR)"

# Full deterministic build: wipe stale doctrees/site first (avoids the
# incremental-state hang on the big ingested 08-lua-nginx-module page), then
# build English, compile existing zh_CN catalogs, and build Chinese.
build: clean html-all

html: html-en

html-en:
	@mkdir -p "$(SITEDIR)"
	SPHINX_LANGUAGE=en $(SPHINXBUILD) -b html -d "$(DOCTREESDIR)/en" "$(SOURCEDIR)" "$(SITEDIR)/en" $(SPHINXOPTS) $(O)

html-loose: SPHINXOPTS := -n
html-loose: html

# Regenerate .pot catalogs (extraction of the huge ingested README page is
# heavy). This is a manual, opt-in step - run it after English sources change,
# before translating .po catalogs.
gettext:
	@mkdir -p "$(BUILDDIR)/gettext"
	$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/gettext" $(SPHINXOPTS) $(O)

intl-update: gettext
	@mkdir -p locale/zh_CN/LC_MESSAGES
	$(SPHINXINTL) update -p "$(BUILDDIR)/gettext" -l zh_CN

translate-zh: intl-update
	$(PYTHON) "$(PKB_SCRIPT_DIR)/translate_po.py" --po-dir locale/zh_CN/LC_MESSAGES

# Compile existing .po -> .mo only. Uses gettext msgfmt (fast and robust on the
# large 2425-entry 08 catalog) instead of Babel's sphinx-intl build.
compile-intl:
	@for po in `find locale/zh_CN/LC_MESSAGES -name '*.po'`; do \
		msgfmt -o "$${po%.po}.mo" "$$po" || exit 1; \
	done
	@echo "Compiled .mo catalogs"

html-zh: compile-intl
	@rm -rf "$(SITEDIR)/zh" "$(SITEDIR)/zh_CN"
	@mkdir -p "$(SITEDIR)"
	SPHINX_LANGUAGE=zh_CN $(SPHINXBUILD) -b html -D language=zh_CN "$(SOURCEDIR)" "$(SITEDIR)/zh" $(SPHINXOPTS) $(O)

build-landing:
	$(PYTHON) "$(PKB_SCRIPT_DIR)/render_landing.py" --site-dir "$(SITEDIR)" --default-language "$(DEFAULT_LANG)"

html-all: html-en html-zh build-landing

serve: html
	$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory "$(SITEDIR)/en"

serve-live: html
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(SITEDIR)/en" $(SPHINXOPTS) $(O) \
		--host 127.0.0.1 --port $(PORT) \
		--ignore "*.swp" \
		--ignore "*.pdf" \
		--ignore "*.log" \
		--ignore "*.out" \
		--ignore "*.toc" \
		--ignore "*.aux" \
		--ignore "*.idx" \
		--ignore "*.ind" \
		--ignore "*.ilg" \
		--ignore "*.tex" \
		--watch . \
		--open-browser

serve-all: html-all
	$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory "$(SITEDIR)"

pkb-check:
	$(PYTHON) "$(PKB_SCRIPT_DIR)/check_pkb_staleness.py" --repo-root "$(PKB_REPO_ROOT)" --doc-dir "$(PKB_DOC_DIR)" $(PKB_ARGS)

pkb-check-i18n:
	@if [ -d "$(PKB_DOC_DIR)/locale/zh_CN/LC_MESSAGES" ]; then \
		$(PYTHON) "$(PKB_SCRIPT_DIR)/check_translation_sync.py" --repo-root "$(PKB_REPO_ROOT)" --doc-dir "$(PKB_DOC_DIR)" $(PKB_ARGS); \
	else \
		echo "No zh_CN catalogs found under $(PKB_DOC_DIR)/locale/zh_CN/LC_MESSAGES; skipping."; \
	fi

pkb-level1:
	bash "$(PKB_SCRIPT_DIR)/update_doc_level1.sh" "$(PKB_REPO_ROOT)" "$(PKB_DOC_DIR)"

pkb-review-status:
	$(PYTHON) "$(PKB_SCRIPT_DIR)/pkb_review_status.py" --doc-dir "$(PKB_DOC_DIR)"

changelog-draft:
	bash "$(PKB_SCRIPT_DIR)/gen_changelog.sh" --repo-root "$(PKB_REPO_ROOT)" --doc-dir "$(PKB_DOC_DIR)"

strip-confidential:
	$(PYTHON) "$(PKB_SCRIPT_DIR)/strip_confidential.py" --site-dir "$(SITEDIR)" --doc-dir "$(PKB_DOC_DIR)" --min-level "$(CONF_MIN_LEVEL)"

agentbox-gen: html-all strip-confidential
	$(PYTHON) "$(AGENTBOX_GEN)" --site-dir "$(SITEDIR)" --out "$(AGENTBOX_FUNC)/files.ts"
	@echo ""
	@echo "AgentBox files.ts regenerated from $(SITEDIR) (pages at >= $(CONF_MIN_LEVEL) stripped)."

agentbox-init:
	@test -f agentbox.yaml || { echo "ERROR: agentbox.yaml not found. Create it first (see templates/sphinx/agentbox.yaml)."; exit 1; }
	@mkdir -p "$(AGENTBOX_FUNC)"
	@test -f "$(AGENTBOX_FUNC)/index.ts" || { echo "Copying index.ts template to $(AGENTBOX_FUNC)/"; cp "$(PKB_SCRIPT_DIR)/../templates/sphinx/functions/doc/index.ts" "$(AGENTBOX_FUNC)/index.ts" 2>/dev/null || echo "WARNING: Could not copy index.ts template. Copy it manually from the skill."; }

agentbox-deploy:
	@test -f agentbox.yaml || { echo "ERROR: agentbox.yaml not found in current directory."; echo "  Create it or run 'make agentbox-init'. abx requires it in cwd."; exit 1; }
	$(ABX) func deploy "$(FUNCTION_SLUG)"

publish-agentbox: agentbox-init agentbox-gen agentbox-deploy
	@echo ""
	@echo "Publish complete."

# Build the full bilingual site and push the result to the GitHub Pages branch.
# The site root is repo-root of $(PAGES_BRANCH), so the en/zh subpaths and the
# landing index.html resolve at https://<account>.github.io/<repo>/.
publish: html-all
	@echo "Publishing $(SITEDIR) to GitHub Pages branch '$(PAGES_BRANCH)' ..."
	@rm -rf "$(PAGES_DIR)"
	@git worktree prune >/dev/null 2>&1 || true
	@if git show-ref --verify --quiet "refs/heads/$(PAGES_BRANCH)"; then \
		git worktree add -f "$(PAGES_DIR)" "$(PAGES_BRANCH)"; \
	else \
		git worktree add -b "$(PAGES_BRANCH)" "$(PAGES_DIR)" HEAD; \
	fi
	@find "$(PAGES_DIR)" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
	@cp -R "$(SITEDIR)/." "$(PAGES_DIR)/"
	@touch "$(PAGES_DIR)/.nojekyll"
	@cd "$(PAGES_DIR)" && git add -A && \
		git -c user.name="GitHub Pages bot" -c user.email="pages@localhost" \
		commit -q -m "docs: publish site $(shell date -u +%Y-%m-%dT%H:%M:%SZ)" && \
		git push origin "$(PAGES_BRANCH)"
	@git worktree remove -f "$(PAGES_DIR)"
	@echo "Published. Site is served from https://<account>.github.io/<repo>/"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
