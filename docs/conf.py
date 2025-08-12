# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DACT Pipeline'
copyright = '2024, DACT Pipeline Team'
author = 'DACT Pipeline Team'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'myst_parser',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Options for MyST parser ------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# -- Options for autodoc ----------------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# -- Options for intersphinx extension --------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'pytest': ('https://docs.pytest.org/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/', None),
}

# -- Options for todo extension ---------------------------------------------
todo_include_todos = True

# -- Options for Napoleon extension -----------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Custom configuration ---------------------------------------------------
html_title = 'DACT Pipeline Documentation'
html_short_title = 'DACT Pipeline'
html_logo = None
html_favicon = None

html_theme_options = {
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

html_context = {
    "display_github": True,
    "github_user": "dact-pipeline",
    "github_repo": "dact-pipeline",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_css_files = [
    'custom.css',
]

# -- Options for LaTeX output -----------------------------------------------
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'preamble': r'''
\usepackage{xeCJK}
\setCJKmainfont{SimSun}
''',
}

latex_documents = [
    ('index', 'dact-pipeline.tex', 'DACT Pipeline Documentation',
     'DACT Pipeline Team', 'manual'),
]

# -- Options for manual page output -----------------------------------------
man_pages = [
    ('index', 'dact-pipeline', 'DACT Pipeline Documentation',
     [author], 1)
]

# -- Options for Texinfo output ---------------------------------------------
texinfo_documents = [
    ('index', 'dact-pipeline', 'DACT Pipeline Documentation',
     author, 'dact-pipeline', 'A data-driven test pipeline for AI chip/compiler.',
     'Miscellaneous'),
]