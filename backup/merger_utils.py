import os
import platform
import platformdirs
from sphinx.ext import apidoc
from sphinx.cmd.build import build_main
import pytest
from bs4 import BeautifulSoup
import tempfile
import shutil
import coverage


def generate_docs():
    try:
        # Create a temporary directory for Sphinx documentation
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = os.path.join(temp_dir, 'docs')
            os.makedirs(docs_dir, exist_ok=True)

            # Create a temporary index.rst file
            index_rst_content = """
.. File Merger documentation master file

Welcome to File Merger's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""
            index_rst_path = os.path.join(docs_dir, 'index.rst')
            with open(index_rst_path, 'w') as f:
                f.write(index_rst_content)

            # Create a temporary conf.py file
            conf_py_content = """
# Configuration file for the Sphinx documentation builder.

project = 'File Merger'
copyright = '2024, Your Name'
author = 'Your Name'

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'alabaster'
html_static_path = ['_static']
"""
            conf_py_path = os.path.join(docs_dir, 'conf.py')
            with open(conf_py_path, 'w') as f:
                f.write(conf_py_content)

            # Generate API documentation
            apidoc_main = apidoc.main(
                ['--force', '--output-dir', docs_dir, '.'])
            print(f"API documentation generated with result: {apidoc_main}")
            if apidoc_main != 0:
                print(f"Error generating API documentation: {apidoc_main}")

            # Build Sphinx documentation
            build_main_args = ['-b', 'html', '-q',
                               docs_dir, os.path.join(docs_dir, '_build')]
            build_main_result = build_main(build_main_args)
            print(
                f"Sphinx documentation built with result: {build_main_result}")
            if build_main_result != 0:
                print(
                    f"Error building Sphinx documentation: {build_main_result}")

            # Copy the generated '_build' directory to a permanent location
            docs_build_dir = os.path.join(docs_dir, '_build')
            permanent_docs_dir = 'docs'
            if os.path.exists(permanent_docs_dir):
                shutil.rmtree(permanent_docs_dir)
            shutil.copytree(docs_build_dir, permanent_docs_dir)

            # Read the generated HTML files
            html_files = ['index.html', 'modules.html',
                          'gui.html', 'merge.html', 'merger_utils.html']
            docs_content = ""

            for file in html_files:
                html_path = os.path.join(permanent_docs_dir, file)
                if os.path.exists(html_path):
                    with open(html_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')

                        # Extract the main content of the HTML file
                        main_content = soup.find('div', class_='body')
                        if main_content:
                            # Format the content for better readability
                            docs_content += f"--- {file} ---\n\n"
                            docs_content += main_content.get_text(
                                separator='\n', strip=True)
                            docs_content += "\n\n"

                else:
                    print(f"Warning: File not found - {html_path}")

            return docs_content

    except Exception as e:
        print(f"Error generating documentation: {str(e)}")
        return ""


def run_tests():
    cov = coverage.Coverage()
    cov.start()
    try:
        pytest.main(['-v', 'test_dummy.py'])
    except Exception as e:
        print(f"Error running tests: {str(e)}")
    finally:
        cov.stop()
        cov.save()
        if os.path.exists('tests.html'):
            with open('tests.html', 'r', encoding='utf-8') as f:
                tests_text = f.read()
        else:
            tests_text = "Testrapport saknas"
        return tests_text


def get_system_info():
    app_dirs = platformdirs.AppDirs("FileMergerApp")
    system_info = f"Operating System: {os.name}\n"
    system_info += f"Python Version: {platform.python_version()}\n"
    system_info += f"User Data Directory: {app_dirs.user_data_dir}\n"
    system_info += f"User Config Directory: {app_dirs.user_config_dir}\n"
    system_info += f"User Cache Directory: {app_dirs.user_cache_dir}\n"
    return system_info


def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    return text
