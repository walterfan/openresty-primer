# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# Author: OpenResty Primer contributors

import os
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'openresty'
copyright = '2026, OpenResty Primer contributors'
author = 'OpenResty Primer contributors'
release = '1.0'
language = os.environ.get("SPHINX_LANGUAGE", "en")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',           # MyST markdown parser
    'sphinx.ext.autodoc',    # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',   # Support for NumPy and Google style docstrings
    'sphinx.ext.viewcode',   # Add links to source code
    'sphinx.ext.intersphinx',# Link to other project's documentation
    'sphinx.ext.todo',       # Support for todo items
    'sphinx.ext.graphviz',   # Support for Graphviz graphs
    'sphinx_copybutton',     # Add copy button to code blocks
    'sphinx_design',         # Design components (cards, tabs, etc.)
    'sphinxcontrib.mermaid', # Mermaid diagrams (primary)
    # Uncomment below and install plantuml.jar to enable PlantUML support:
    # 'sphinxcontrib.plantuml',
]

# MyST parser configuration
myst_enable_extensions = [
    "amsmath",          # LaTeX math
    "colon_fence",      # ::: fence for directives
    "deflist",          # Definition lists
    "dollarmath",       # $...$ for inline math
    "fieldlist",        # Field lists
    "html_admonition",  # HTML admonitions
    "html_image",       # HTML images
    "linkify",          # Auto-detect URLs
    "replacements",     # Text replacements
    "smartquotes",      # Smart quotes
    "strikethrough",    # ~~strikethrough~~
    "substitution",     # {{ variable }}
    "tasklist",         # - [ ] task lists
]

# MyST parser settings
myst_heading_anchors = 3  # Auto-generate anchors for headings up to level 3
myst_footnote_transition = True
myst_dmath_double_inline = True
myst_fence_as_directive = ["mermaid"]  # treat ```mermaid fences as Sphinx directives
# The ingested 08-lua-nginx-module page is ~9,700 lines of dense prose with
# thousands of inline links; fuzzy URL auto-linking over that text can hit
# pathological regex backtracking (a build that spins at 100% CPU during
# gettext / html). We use explicit links everywhere, so disable fuzzy linking.
myst_linkify_fuzzy_links = False

templates_path = ['_templates']
exclude_patterns = ['_build', '_generated', '.venv', '**/__pycache__', 'Thumbs.db', '.DS_Store', '**.ipynb_checkpoints', 'README.md']
# The ingested 08-lua-nginx-module page contains many code blocks (e.g. nginx
# with braced Lua) that the Pygments "nginx" lexer cannot tokenize. Sphinx falls
# back to a relaxed highlight, so suppress the cosmetic warning to keep strict
# (-W) builds green.
suppress_warnings = ['misc.highlighting_failure', 'myst.xref_missing', 'image.not_readable']
locale_dirs = ['locale/']
gettext_compact = False
gettext_uuid = True

# The suffix(es) of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'  # Read the Docs theme
# html_theme = 'furo'  # Alternative: Modern, clean theme

html_static_path = ['_static']
html_context = {
    "available_languages": [
        {"code": "en", "route": "en", "label": "English"},
        {"code": "zh_CN", "route": "zh", "label": "中文"},
    ],
    "language_routes": {
        "en": "en",
        "zh_CN": "zh",
    },
    "current_language": language,
}

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

# Custom CSS
html_css_files = [
    'custom.css',
]

# Logo and favicon
# html_logo = '_static/logo.png'
# html_favicon = '_static/favicon.ico'

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'preamble': '',
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files
latex_documents = [
    (master_doc, 'project.tex', 'Project Documentation',
     author, 'manual'),
]

# -- Options for manual page output ------------------------------------------

man_pages = [
    (master_doc, 'project', 'Project Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

texinfo_documents = [
    (master_doc, 'project', 'Project Documentation',
     author, 'project', 'Project description.',
     'Miscellaneous'),
]

# -- Extension configuration -------------------------------------------------

# This Lua manual has no external Python references; keep builds offline.
intersphinx_mapping = {}

# sphinx.ext.todo
todo_include_todos = True

# sphinx.ext.autodoc
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# -- Translate MyST document titles via doctree-resolved event ---------------
# MyST-parser's first `# heading` becomes a title node that Sphinx's i18n
# transform does not translate. This hook patches the title after all other
# transforms have run.

def _translate_titles(app, doctree, docname):
    """Translate top-level title nodes that Sphinx's i18n missed.

    Sphinx's i18n transform does not translate section titles that carry a
    numeric prefix such as `1. Lua at a Glance`. Run our own lookup over every
    title node: already-translated nodes are unchanged (gettext returns the
    input when there is no match), so this is safe alongside the built-in
    transform.
    """
    if app.config.language == 'en':
        return
    import gettext as _gettext
    from docutils import nodes
    try:
        t = _gettext.translation(
            docname, localedir=str(app.srcdir / 'locale'),
            languages=[app.config.language])
    except FileNotFoundError:
        return
    for node in doctree.traverse(nodes.title):
        orig = node.astext()
        translated = t.gettext(orig)
        if translated != orig:
            node.clear()
            node += nodes.Text(translated)
            # Keep the sidebar, breadcrumb, and <title> tag aligned on the
            # document title node only.
            if app.env.titles.get(docname) is node:
                app.env.titles[docname] = node
                app.env.longtitles[docname] = node
    # Document (first) title drives the sidebar/breadcrumb/<title> tag.
    for node in doctree.traverse(nodes.title):
        app.env.titles[docname] = node
        app.env.longtitles[docname] = node
        break



# Render a documents metadata footer without changing this manual's theme or content.
from pathlib import Path as _MetadataPath
import sys as _metadata_sys
_metadata_sys.path.insert(0, str(_MetadataPath(__file__).resolve().parents[0] / "scripts"))
from pkb_metadata_footer import _inject_pkb_metadata


def setup(app):
    app.connect('doctree-resolved', _translate_titles)
    app.connect('doctree-resolved', _inject_pkb_metadata)

# -- Custom configuration ----------------------------------------------------

html_show_sourcelink = False
html_show_sphinx = False
add_module_names = False

# -- Mermaid configuration ---------------------------------------------------

# Mermaid version (use latest stable)
mermaid_version = "10.6.1"

# Mermaid initialization config
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    logLevel: 'error',
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
    },
    sequence: {
        useMaxWidth: true,
        diagramMarginX: 50,
        diagramMarginY: 10,
        actorMargin: 50,
        width: 150,
        height: 65,
        boxMargin: 10,
        boxTextMargin: 5,
        noteMargin: 10,
        messageMargin: 35,
        mirrorActors: true,
        bottomMarginAdj: 1,
        useMaxWidth: true,
        rightAngles: false,
        showSequenceNumbers: false
    },
    gantt: {
        titleTopMargin: 25,
        barHeight: 20,
        barGap: 4,
        topPadding: 50,
        leftPadding: 75,
        gridLineStartPadding: 35,
        fontSize: 11,
        numberSectionStyles: 4,
        axisFormat: '%Y-%m-%d'
    }
});
"""

# -- PlantUML configuration (disabled by default) ----------------------------
# To enable PlantUML:
#   1. Uncomment 'sphinxcontrib.plantuml' in the extensions list above
#   2. Uncomment one of the plantuml options below
#   3. Ensure plantuml.jar is available or use the server URL
#
# Option 1: Local jar file
# plantuml = 'java -jar /path/to/plantuml.jar'
# plantuml_output_format = 'svg'
#
# Option 2: PlantUML server (recommended for CI/CD)
# plantuml = 'java -jar plantuml.jar'
# plantuml_output_format = 'svg'
#
# Option 3: Public PlantUML server (not recommended for production)
# plantuml_server_url = 'http://www.plantuml.com/plantuml'
# plantuml_output_format = 'svg'

# -- Graphviz configuration --------------------------------------------------

graphviz_output_format = 'svg'
