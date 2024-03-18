import pytest
from gui import FileMergerApp, GenerateExtraInfoThread
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QEventLoop
from fpdf import FPDF
import os
import sqlite3


@pytest.fixture
def app(qtbot):
    app = FileMergerApp()
    qtbot.addWidget(app)
    return app


def test_merge_files_no_output_file(app, mocker, qtbot):
    app.files = ["file1.txt", "file2.txt"]
    mocker.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", ""))
    qtbot.mouseClick(app.merge_button, Qt.LeftButton)
    assert "Ingen utdatafil vald." in app.merge_button.toolTip()


def test_merge_files_success(app, mocker, qtbot):
    app.files = ["file1.txt", "file2.txt"]
    mocker.patch.object(
        QtWidgets.QFileDialog, "getSaveFileName", return_value=("output.pdf", "")
    )
    thread_mock = mocker.patch.object(
        GenerateExtraInfoThread, "generate_extra_info", return_value=None
    )
    mocker.patch.object(FPDF, "output", return_value=None)

    try:
        with qtbot.waitSignal(app.thread.finished, timeout=5000):
            app.start_generate_extra_info_thread()
    except AttributeError as e:
        pytest.fail(f"Trådens 'finished'-signal hittades inte: {str(e)}")

    assert thread_mock.called
    assert app.generate_extra_info_thread.include_sphinx == False


def test_print_database_info(app, mocker):
    pdf_mock = mocker.MagicMock()
    mocker.patch.object(app, "files", ["test.db"])
    mocker.patch.object(pdf_mock, "set_font", return_value=None)
    mocker.patch.object(pdf_mock, "cell", return_value=None)
    mocker.patch.object(pdf_mock, "ln", return_value=None)

    conn = sqlite3.connect("test.db")
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS test_table")
    c.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO test_table (name) VALUES ('Test Entry')")
    conn.commit()
    conn.close()

    app.print_database_info(pdf_mock, "test.db")
    pdf_mock.set_font.assert_called()
    pdf_mock.cell.assert_called()
    pdf_mock.ln.assert_called()

    os.remove("test.db")

    conn = sqlite3.connect("test.db")
    c = conn.cursor()
    c.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO test_table (name) VALUES ('Test Entry')")
    conn.commit()
    conn.close()

    app.print_database_info(pdf_mock, "test.db")
    pdf_mock.set_font.assert_called()
    pdf_mock.cell.assert_called()
    pdf_mock.ln.assert_called()

    os.remove("test.db")
