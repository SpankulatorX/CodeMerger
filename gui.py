import os
import traceback
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QObject
from fpdf import FPDF
import sqlite3
from merger_utils import (
    generate_docs,
    run_tests,
    get_system_info,
    extract_text_from_html,
)
import logging
import re
from bs4 import BeautifulSoup
from html.parser import HTMLParser


class GenerateExtraInfoThread(QObject):
    extra_info_generated = pyqtSignal(str, str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, include_sphinx):
        super().__init__()
        self.include_sphinx = include_sphinx

    def generate_extra_info(self):
        logging.info("Entering generate_extra_info method")
        try:
            docs_text = ""
            if self.include_sphinx:
                logging.info("Generating Sphinx documentation")
                docs_text = generate_docs()
            logging.info("Running tests")
            tests_text = run_tests()
            logging.info("Getting system info")
            system_info = get_system_info()
            tests_html_path = os.path.join(os.path.dirname(__file__), "tests.html")
            logging.info(f"tests_html_path: {tests_html_path}")
            if os.path.exists(tests_html_path):
                logging.info("tests.html exists, reading its content")
                with open(tests_html_path, "r", encoding="utf-8") as f:
                    tests_text = f.read()
            else:
                logging.warning("tests.html does not exist")
                tests_text = "Testrapport saknas"
            logging.info("Emitting extra_info_generated signal")
            self.extra_info_generated.emit(docs_text, tests_text, system_info)
        except Exception as e:
            logging.exception(f"Error in generate_extra_info method: {str(e)}")
            self.error_occurred.emit(str(e))


class FileMergerApp(QWidget):
    def __init__(self, files=None, testing=False):
        super().__init__()
        self.files = files or []
        self.new_page = False
        self.include_sphinx = False
        self.output_file_name = ""
        self.testing = testing
        self.initialize_ui()
        self.new_page_checkbutton.setChecked(self.new_page)
        self.include_sphinx_checkbutton.setChecked(self.include_sphinx)

        self.new_page_checkbutton.stateChanged.connect(self.toggle_new_page)
        self.include_sphinx_checkbutton.stateChanged.connect(self.toggle_include_sphinx)

    def initialize_ui(self):
        self.setWindowTitle("File Merger")

        layout = QVBoxLayout()

        self.browse_button = QPushButton("Välj filer")
        self.browse_button.clicked.connect(self.browse_files)
        layout.addWidget(self.browse_button)

        self.merge_button = QPushButton("Sammanslå filer")
        self.merge_button.clicked.connect(self.merge_files)
        layout.addWidget(self.merge_button)

        self.new_page_checkbutton = QCheckBox("Starta varje dokument på en ny sida")
        layout.addWidget(self.new_page_checkbutton)

        self.include_sphinx_checkbutton = QCheckBox("Inkludera Sphinx-dokumentation")
        layout.addWidget(self.include_sphinx_checkbutton)

        self.setLayout(layout)

    def browse_files(self):
        self.files, _ = QFileDialog.getOpenFileNames(
            self, "Välj filer", os.path.expanduser("~"), "Alla filer (*.*);;"
        )
        if not self.files:
            QMessageBox.information(self, "Information", "Inga filer valdes.")
            logging.info("Inga filer valdes.")
        else:
            file_list = "\n".join(self.files)
            QMessageBox.information(
                self, "Information", f"{len(self.files)} fil(er) valda:\n{file_list}"
            )
            logging.info(f"{len(self.files)} fil(er) valda:\n{file_list}")

    def merge_files(self):
        try:
            logging.info("Entering merge_files method")
            if not self.files:
                if not self.testing:
                    QMessageBox.warning(
                        self, "Varning", "Välj filer att sammanslå först."
                    )
                logging.warning("Välj filer att sammanslå först.")
                self.merge_button.setToolTip("Välj filer att sammanslå först.")
                logging.info("No files selected, exiting merge_files method")
                return

            logging.info("Files selected, continuing with merge process")
            self.output_file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Spara som",
                os.path.expanduser("~"),
                "PDF fil (*.pdf);;Text fil (*.txt)",
            )
            logging.info(f"Selected output file: {self.output_file_name}")
            if not self.output_file_name:
                QMessageBox.warning(self, "Varning", "Ingen utdatafil vald.")
                logging.warning("Ingen utdatafil vald.")
                return

            logging.info("Sammanfogning påbörjad")
            logging.info(f"Valda filer: {self.files}")

            # Kontrollera om self.files innehåller giltiga filer
            for file in self.files:
                if not os.path.isfile(file):
                    QMessageBox.warning(self, "Varning", f"Filen {file} finns inte.")
                    logging.warning(f"Filen {file} finns inte.")
                    return

            self.start_generate_extra_info_thread()

        except Exception as e:
            logging.error(f"Ett fel uppstod i merge_files-metoden: {str(e)}")
            raise

    def start_generate_extra_info_thread(self):
        self.generate_extra_info_thread = GenerateExtraInfoThread(self.include_sphinx)
        self.thread = QThread()
        self.generate_extra_info_thread.moveToThread(self.thread)
        self.thread.started.connect(self.generate_extra_info_thread.generate_extra_info)
        self.generate_extra_info_thread.extra_info_generated.connect(
            self.on_extra_info_generated
        )
        self.generate_extra_info_thread.error_occurred.connect(self.on_extra_info_error)
        self.generate_extra_info_thread.extra_info_generated.connect(self.thread.quit)
        # Remove the following line
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_merge_completed(self):
        logging.info("Sammanslagning klar")
        QMessageBox.information(self, "Information", "Sammanslagning utförd.")

    def toggle_new_page(self, state):
        self.new_page = state == Qt.Checked

    def toggle_include_sphinx(self, state):
        self.include_sphinx = state == Qt.Checked

    def on_extra_info_generated(self, docs_text, tests_text, system_info):
        logging.info("Entering on_extra_info_generated method")
        try:
            if not self.output_file_name:
                logging.error("Ingen utdatafil vald.")
                QMessageBox.critical(self, "Fel", "Ingen utdatafil vald.")
            return
            if self.output_file_name.endswith(".pdf"):
                logging.info("Generating PDF file")
                pdf = FPDF()
                font_file = os.path.join(
                    os.path.dirname(__file__), "DejaVuSansCondensed.ttf"
                )
                font_file_bold = os.path.join(
                    os.path.dirname(__file__), "DejaVuSansCondensed-Bold.ttf"
                )

                if not os.path.exists(font_file) or not os.path.exists(font_file_bold):
                    QMessageBox.warning(
                        self,
                        "Varning",
                        "Kunde inte hitta nödvändiga fontfiler. PDF-generering avbruten.",
                    )
                    logging.warning(
                        "Kunde inte hitta nödvändiga fontfiler. PDF-generering avbruten."
                    )
                    return

                pdf.add_font("DejaVu", "", font_file, uni=True)
                pdf.add_font("DejaVu", "B", font_file_bold, uni=True)
                pdf.set_font("DejaVu", "", 12)
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_margins(left=20, top=20, right=20)
                pdf.alias_nb_pages()

                # Lägg till separata sidor för varje sektion
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Innehållsförteckning", ln=True, align="C")
                pdf.ln(10)

                sphinx_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Sphinx-dokumentation", link=sphinx_bookmark)
                pdf.ln()

                system_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Systeminformation", link=system_bookmark)
                pdf.ln()

                test_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Testrapport", link=test_bookmark)
                pdf.ln()

                python_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Python-filer", link=python_bookmark)
                pdf.ln()

                database_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Databasfiler", link=database_bookmark)
                pdf.ln()

                log_bookmark = pdf.add_link()
                pdf.cell(0, 10, "Loggfiler", link=log_bookmark)
                pdf.ln()

                # Sphinx-dokumentation
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Sphinx-dokumentation", ln=True, align="L")
                pdf.set_font("DejaVu", "", 12)
                pdf.ln(5)
                pdf.set_link(sphinx_bookmark)
                if self.include_sphinx:
                    pdf.multi_cell(0, 6, docs_text, align="L")

                # Systeminformation
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Systeminformation", ln=True, align="L")
                pdf.set_font("DejaVu", "", 12)
                pdf.ln(5)
                pdf.set_link(pdf.add_link())
                for line in system_info.split("\n"):
                    pdf.multi_cell(0, 6, line, align="L")

                # Testrapport
                pdf.add_page()
                test_bookmark = pdf.add_link()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Testrapport", ln=True, align="L")
                pdf.set_font("DejaVu", "", 12)
                pdf.ln(5)
                pdf.set_link(test_bookmark)
                pdf.multi_cell(0, 6, tests_text, align="L")

                # Python-filer
                python_bookmark = pdf.add_link()
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Python-filer", ln=True, align="L")
                pdf.ln(5)
                pdf.set_link(pdf.add_link())

                for file in self.files:
                    if file.endswith(".py"):
                        pdf.set_font("DejaVu", "B", 12)
                        pdf.cell(0, 10, f"Filsökväg: {file}", ln=True, align="L")
                        pdf.cell(
                            0,
                            10,
                            f"Filnamn: {os.path.basename(file)}",
                            ln=True,
                            align="L",
                        )
                        pdf.set_font("DejaVu", "", 12)
                        pdf.ln(5)

                        with open(file, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()

                        # Split the content into lines
                        lines = content.split("\n")

                        # Iterate over the lines and add them to the PDF
                        for line in lines:
                            # Check if the line is too long to fit within the page width
                            if pdf.get_string_width(line) > pdf.w - 40:
                                # Split the line into multiple lines
                                words = line.split()
                                new_line = ""
                                for word in words:
                                    if (
                                        pdf.get_string_width(new_line + " " + word)
                                        < pdf.w - 40
                                    ):
                                        new_line += " " + word
                                    else:
                                        pdf.multi_cell(0, 6, new_line, align="L")
                                        new_line = word
                                # Add the remaining line
                                pdf.multi_cell(0, 6, new_line, align="L")
                            else:
                                pdf.multi_cell(0, 6, line, align="L")

                        pdf.ln(5)

                        if self.new_page:
                            pdf.add_page()
                        else:
                            pdf.ln(5)

                # Databasfiler
                database_bookmark = pdf.add_link()
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Databasfiler", ln=True, align="L")
                pdf.ln(5)
                pdf.set_link(pdf.add_link())

                for file in self.files:
                    if file.endswith(".db"):
                        pdf.set_font("DejaVu", "B", 12)
                        pdf.cell(0, 10, f"Filsökväg: {file}", ln=True, align="L")
                        pdf.cell(
                            0,
                            10,
                            f"Filnamn: {os.path.basename(file)}",
                            ln=True,
                            align="L",
                        )
                        pdf.set_font("DejaVu", "", 12)
                        pdf.ln(5)
                        self.print_database_info(pdf, file)

                        if self.new_page:
                            pdf.add_page()
                        else:
                            pdf.ln(5)

                # Loggfiler
                log_bookmark = pdf.add_link()
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Loggfiler", ln=True, align="L")
                pdf.ln(5)
                pdf.set_link(pdf.add_link())

                for file in self.files:
                    if file.endswith(".log"):
                        pdf.set_font("DejaVu", "B", 12)
                        pdf.cell(0, 10, f"Filsökväg: {file}", ln=True, align="L")
                        pdf.cell(
                            0,
                            10,
                            f"Filnamn: {os.path.basename(file)}",
                            ln=True,
                            align="L",
                        )
                        pdf.set_font("DejaVu", "", 12)
                        pdf.ln(5)

                        with open(file, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Split the content into lines
                        lines = content.split("\n")

                        # Iterate over the lines and add them to the PDF
                        for line in lines:
                            # Check if the line is too long to fit within the page width
                            if pdf.get_string_width(line) > pdf.w - 40:
                                # Split the line into multiple lines
                                words = line.split()
                                new_line = ""
                                for word in words:
                                    if (
                                        pdf.get_string_width(new_line + " " + word)
                                        < pdf.w - 40
                                    ):
                                        new_line += " " + word
                                    else:
                                        pdf.multi_cell(0, 6, new_line, align="L")
                                        new_line = word
                                # Add the remaining line
                                pdf.multi_cell(0, 6, new_line, align="L")
                            else:
                                pdf.multi_cell(0, 6, line, align="L")

                        pdf.ln(5)

                        if self.new_page:
                            pdf.add_page()
                        else:
                            pdf.ln(5)

                try:
                    pdf.output(self.output_file_name)
                    logging.info(f"Sammanslagen fil skapad: {self.output_file_name}")
                except Exception as e:
                    logging.error(
                        f"Ett fel uppstod vid skapande av sammanslagen fil: {str(e)}"
                    )
                    QMessageBox.critical(
                        self,
                        "Fel",
                        f"Ett fel uppstod vid skapande av sammanslagen fil: {str(e)}",
                    )
            else:
                logging.warning("Endast PDF-format stöds för närvarande.")
                QMessageBox.warning(
                    self, "Varning", "Endast PDF-format stöds för närvarande."
                )
        except Exception as e:
            logging.error(f"Ett fel uppstod vid generering av PDF-fil: {str(e)}")
            QMessageBox.critical(
                self, "Fel", f"Ett fel uppstod vid generering av PDF-fil: {str(e)}"
            )

    def on_extra_info_error(self, error_msg):
        QMessageBox.critical(
            self,
            "Fel",
            f"Ett fel uppstod vid generering av extra information: {error_msg}",
        )
        logging.error(f"Fel vid generering av extra information: {error_msg}")

    def toggle_new_page(self, state):
        self.new_page = state == Qt.Checked
        self.new_page_checkbutton.setChecked(self.new_page)

    def toggle_include_sphinx(self, state):
        self.include_sphinx = state == Qt.Checked
        self.include_sphinx_checkbutton.setChecked(self.include_sphinx)

    def print_database_info(self, pdf, file):
        try:
            conn = sqlite3.connect(file)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            if not tables:
                pdf.cell(0, 10, "Databasen är tom.", ln=True, align="L")
                pdf.ln(5)
                return

            for table in tables:
                pdf.set_font("DejaVu", "B", 12)
                pdf.cell(0, 10, f"Tabell: {table[0]}", ln=True, align="L")
                pdf.set_font("DejaVu", "", 12)
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()

                for column in columns:
                    pdf.cell(
                        0,
                        10,
                        f"  Kolumn: {column[1]}, Typ: {column[2]}",
                        ln=True,
                        align="L",
                    )

                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                row_count = cursor.fetchone()[0]
                pdf.cell(0, 10, f"  Antal rader: {row_count}", ln=True, align="L")
                pdf.ln(5)

            conn.close()

        except Exception as e:
            QMessageBox.critical(
                self, "Fel", f"Ett fel uppstod vid läsning av databasen: {str(e)}"
            )
            logging.error(f"Fel vid läsning av databasen: {str(e)}")
            pdf.ln(5)
