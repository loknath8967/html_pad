from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys, os, pathlib, threading
from urllib.request import pathname2url
import pandas as pd
from PyQt5.QtWebEngineWidgets import *



def format(color, style=''):
    """
    Return a QTextCharFormat with the given attributes.
    """
    _color = QColor()
    if type(color) is not str:
        _color.setRgb(color[0], color[1], color[2])
    else:
        _color.setNamedColor(color)
    _format = QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    return _format


STYLES = {
    'tags': format([255, 255, 0], 'italic'),
    'tags_id': format([229, 132, 22], 'bold'),
    'operator': format([124, 252, 0], 'italic'),
    'font': format([255, 255, 255]),
    'type': format([30, 144, 255]),
    'head': format([148, 0, 211]),
    'string': format([0, 255, 255], 'italic'),
    'string2': format([0, 255, 255], 'italic'),
    'comment': format([128, 128, 128]),
    'numbers': format([100, 150, 190]),
}


class HTML_Sentext(QSyntaxHighlighter):
    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)
        self.tri_single = (QRegExp("'''"), 1, STYLES['string2'])
        self.tri_double = (QRegExp('"""'), 2, STYLES['string2'])
        rules = []
        rules += [
            (r'<[A-z].*.>', 0, STYLES['operator']),
            (r'(<\w+)|</\w+>', 0, STYLES['tags']),
            (r'<!\w+.*.>|<!\w+>', 0, STYLES['font']),
            (r'<!DOCTYPE \w+', 0, STYLES['type']),
            (r'<!\DOCTYPE', 0, STYLES['head']),
            (r'>.*.<', 0, STYLES['font']),
            (r'>|<', 0, STYLES['tags_id']),
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, STYLES['string']),
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, STYLES['string']),
            (r'#[^\n]*', 0, STYLES['comment']),
            (r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, STYLES['numbers']),
        ]
        self.rules = [(QRegExp(pat), index, fmt)
                      for (pat, index, fmt) in rules]

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)
            while index >= 0:
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            self.match_multiline(text, *self.tri_double)

    def match_multiline(self, text, delimiter, in_state, style):
        """Do highlighting of multi-line strings. ``delimiter`` should be a
        ``QRegExp`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            start = delimiter.indexIn(text)
            add = delimiter.matchedLength()
        while start >= 0:
            end = delimiter.indexIn(text, start + add)
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            self.setFormat(start, length, style)
            start = delimiter.indexIn(text, start + length)
        if self.currentBlockState() == in_state:
            return True
        else:
            return False


class Completer(QCompleter):
    def __init__(self):
        super(Completer, self).__init__()
        tags = [
            'ul', 'li', 'dl', 'dt', 'dd', 'img', 'area', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'abbr',
            'acronym', 'address', 'bdo', 'q', 'code', 'del', 'br', 'form', 'input', 'textarea', 'caption', 'table',
            'select', 'option', 'button', 'label', 'legend', 'table', 'tr', 'td', 'th', 'col', 'script', 'meta', 'link'
        ]
        self.all_autocomplete_words = []
        self.auto_completion_words = {}

        self.all_autocomplete_words.extend(tags)
        self.all_autocomplete_words = pd.Series(self.all_autocomplete_words).sort_values().drop_duplicates().tolist()
        _model = QStringListModel(self.all_autocomplete_words, self)
        self.setModel(_model)
        self.setModelSorting(self.CaseInsensitivelySortedModel)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setWrapAround(False)


class TEXT_EDITOR(QTextEdit):
    def __init__(self, parent, FileName):
        super(TEXT_EDITOR, self).__init__()
        self.textChanged.connect(
            lambda: threading.Thread(target=parent.WebSiteReload.emit, args=(self.toPlainText(), FileName)).start())
        self.setPlaceholderText('Write Here.......................')
        self.setStyleSheet("""
        QTextEdit{
	font-family:'Consolas'; 
	color: rgb(255,255,255); 
	font-size:18px;
	background-color: #2b2b2b;
	}

	""")


class HTML_EDITOR(QTextEdit):
    def __init__(self, parent, FileName):
        super(HTML_EDITOR, self).__init__()
        self.textChanged.connect(
            lambda: threading.Thread(target=parent.WebSiteUpdate.emit, args=(self.toPlainText(), FileName)).start())
        self.highlight = HTML_Sentext(self.document())
        completer = Completer()
        self.setPlaceholderText('Write html Code only..........................')
        self._completer = None
        self.all_autocomplete = completer.all_autocomplete_words
        self.completion_prefix = ''
        self.setCompleter(completer)

        self.setStyleSheet("""QTextEdit{
	font-family:'Consolas'; 
	color: rgb(255,255,255); 
	font:14px;
	background-color: #2b2b2b;}""")

    def setCompleter(self, c):
        self._completer = c
        c.setWidget(self)
        c.setCompletionMode(QCompleter.PopupCompletion)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        fill_text = {'input': ' type = " " value = "" > ', 'br': ">", 'option': ' value="" ></option>',
                     'a': ' href="" ></a>',
                     'img': ' src="" >', 'meta': '  name="viewport" content="width=device-width, initial-scale=1.0">',
                     'script': ' type="text/javascript"  src=".js" ></script>',
                     'link': ' rel="stylesheet"  type="text/css"  href="" >'}
        if self._completer.widget() is not self:
            return
        tc = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        if self.completion_prefix.lower() == completion[-extra:].lower():
            pass
        else:
            try:
                tc.insertText(
                    f"{completion[-extra:]}{fill_text[completion] if completion in fill_text.keys() else f'></{completion}>'}")
                self.setTextCursor(tc)
                self._completer.setModel(QStringListModel(self.all_autocomplete, self._completer))
            except Exception:
                pass

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def focusInEvent(self, e):
        if self._completer is not None:
            self._completer.setWidget(self)
        super(HTML_EDITOR, self).focusInEvent(e)

    def keyPressEvent(self, e):
        isShortcut = False
        if self._completer is not None and self._completer.popup().isVisible():
            if e.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                e.ignore()
                return
        if e.key() == Qt.Key_E and e.modifiers() == Qt.ControlModifier:
            words = self.all_autocomplete
            self._completer.setModel(QStringListModel(words, self._completer))
            isShortcut = True
        if e.key() == Qt.Key_Period:
            self.textCursor().insertText('')
            self.moveCursor(QtGui.QTextCursor.PreviousWord)
            self.moveCursor(QtGui.QTextCursor.PreviousWord, QtGui.QTextCursor.KeepAnchor)
            dict_key = self.textCursor().selectedText().upper()
            self.moveCursor(QtGui.QTextCursor.NextWord)
            self.moveCursor(QtGui.QTextCursor.NextWord)
            try:
                words = self.auto_complete_dict[dict_key]
                self._completer.setModel(QStringListModel(words, self._completer))
                isShortcut = True
            except:
                pass
        if self._completer is None or not isShortcut:
            super(HTML_EDITOR, self).keyPressEvent(e)
        ctrlOrShift = e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        if self._completer is None or (ctrlOrShift and len(e.text()) == 0):
            return
        eow = "~!@#$%^&*()_+{}|:\">?,./;'[]\\-="
        hasModifier = (e.modifiers() != Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()
        self.completion_prefix = completionPrefix

        if not isShortcut and (hasModifier or len(e.text()) == 0 or len(completionPrefix) < 1 or e.text()[-1] in eow):
            self._completer.popup().hide()
            return
        if completionPrefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(completionPrefix)
            self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(
            0) + self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completer.complete(cr)

class WebSite(QWebEngineView):
    def __init__(self):
        super(WebSite, self).__init__()

class BROWSER(QWidget):
    def __init__(self):
        super(BROWSER, self).__init__()
        Layout=QGridLayout()
        self.UrlBar=QLineEdit()
        self.UrlBar.setReadOnly(True)
        Layout.addWidget(self.UrlBar)
        self.web=WebSite()
        Layout.addWidget(self.web)
        self.setLayout(Layout)

    def Update(self, Page, Url):
        self.web.setUrl(QUrl(f'file:{pathname2url(Url)}'))
        self.UrlBar.setText(f'file:{pathname2url(Url)}')
        threading.Thread(target=self.FileSave, args=(Url, Page)).start()

    def Reload(self, Page, Url):
        self.web.reload()
        self.UrlBar.setText(f'file:{pathname2url(Url)}')
        threading.Thread(target=self.FileSave, args=(Url, Page)).start()


    @staticmethod
    def FileSave(path, data):
        file=open(path, 'w+')
        file.write(data)
        file.close()

class CreateFile(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowIcon(QIcon("file.ico"))
        self.Editor = None
        self.oldPos = None
        self.extension = None
        self.setStyleSheet("""background-color:rgb(96,96,96);""")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setModal(True)
        name_layout = QGridLayout()
        self.setFixedSize(270, 120)
        title = QLabel("New File Name")
        title.setStyleSheet(
            """ QLabel{
            background-color: rgb(96,96,96);
            color:white;font-family:lucida calligraphy;
            font-size:15px;font-weight: 900;

        } """)
        title.setAlignment(Qt.AlignCenter)
        name_layout.addWidget(title, 0, 0, 1, 3)
        Name = QLineEdit()
        Name.setStyleSheet(
            """ QLineEdit{
            background-color:rgb(56,56,56);
            color:white;
            border:1px solid white; 
            border-radius: 7px;
            padding-left:5px;
            padding-right:5px;
            font-family:lucida handwriting;
            font-size: 18px;           
         }""")
        Name.setFixedSize(250, 29)
        Name.setPlaceholderText("Enter File Name ")
        name_layout.addWidget(Name, 1, 0, 1, 2, Qt.AlignRight)

        submit = QPushButton("Ok ")
        submit.setStyleSheet("""
                    QPushButton{
                    background-color: rgb(96,96,96);
                    border:1px hidden white;
                    color:white;
                    font-widget:bold;
                    text-align:center;
                    font-size:15px;
                    font-family:Mv Boli;
                    font-weight: 900;
                }
                 ::hover{
                    background-color: green;
                    border:1px hidden white;
                    border-radius: 7px;
                    color:white;
                    font-size:15px;
                    font-family:Mv Boli;
                    font-weight: 900;
                 }
                 """)
        submit.pressed.connect(lambda: (parent.addTab(f"{Name.text()}{self.extension}"),
                                        Name.clear(), self.close()))
        submit.setFixedSize(51, 25)
        name_layout.addWidget(submit, 2, 1, Qt.AlignRight)

        self.fileType = QLineEdit()
        self.fileType.setToolTip("   File Type   ")
        self.fileType.setFixedSize(125, 29)
        self.fileType.setReadOnly(True)
        self.fileType.setStyleSheet(
            """ QLineEdit{
            background-color:rgb(56,56,56);
            color:white;
            border:1px solid white; 
            border-radius: 7px;
            padding-left:5px;
            padding-right:5px;
            color:white;font-family:lucida calligraphy;
            font-size: 10px; 
            font-weight: 900;          
         }""")
        name_layout.addWidget(self.fileType, 2, 0, Qt.AlignRight)

        close = QPushButton("Cancel")
        close.setStyleSheet("""
            QPushButton{
            background-color: rgb(96,96,96);
            border:1px hidden white;
            color:red;
            font-size:15px;
            font-family:Mv Boli;
            font-weight: 900;
        }
         ::hover{
            background-color: red;
            border-radius: 7px;
            border:1px hidden white;
            color:white;
            font-size:15px;
            font-family:Mv Boli;
            font-weight: 900;
         }

         """)
        close.pressed.connect(self.close)
        close.setFixedSize(55, 25)
        name_layout.addWidget(close, 2, 2)
        self.setLayout(name_layout)

    def Update(self, txt, extension):
        self.fileType.setText(txt)
        self.extension = extension

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()


class FileType(QAction):
    def __init__(self, Name, Tip, ext, parent):
        super(FileType, self).__init__()
        self.setText(Name)
        parent.Create = CreateFile(parent)
        self.setStatusTip(Tip)
        self.setToolTip(Tip)
        self.setParent(parent)
        self.triggered.connect(lambda: (parent.Create.Update(Name, extension=ext), parent.Create.exec_()))


class ITEM(QAction):
    def __init__(self, Name, Shortcut, Tip, Action, parent):
        super(ITEM, self).__init__()
        self.setText(Name)
        self.setStatusTip(Tip)
        self.setShortcut(Shortcut)
        self.setToolTip(Tip)
        self.setParent(parent)
        self.triggered.connect(Action)


class MainWindow(QMainWindow):
    WebSiteUpdate = pyqtSignal(str, str)
    WebSiteReload = pyqtSignal(str, str)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowIcon(QIcon("file.ico"))

        MenuBar = self.menuBar()
        self.shortcut = QShortcut(QKeySequence("Esc"), self)
        self.shortcut.activated.connect(lambda: (self.showMaximized(), MenuBar.setVisible(True)))

        FileMenu = MenuBar.addMenu(" File ")
        FileMenu.addAction(QAction("New Project ", self))
        #               #############            ###########################
        NewFile = QMenu("New ", self)
        NewFile.addAction(FileType("PHP (*.php)", "PHP File", ".php", self))
        NewFile.addAction(FileType("HTML5 (*.html)", "HTML File", ".html", self))
        NewFile.addAction(FileType("StyleSheet (*.css)", "StyleSheet File", ".css", self))
        NewFile.addAction(FileType("JavaScript (*.js)", "JavaScript", ".js", self))
        FileMenu.addMenu(NewFile)
        #
        FileMenu.addAction(ITEM("Open File", "Ctrl+O", "Open File", self.Open, self))
        FileMenu.addAction(ITEM("Save As", "Ctrl+Shift+S", "Save As", self.SaveAs, self))
        FileMenu.addAction(ITEM("Exit", "Ctrl+Q", "Exit", self.close, self))

        # ''''''''''''''''''''''''''''''''''''''''''''           ''''''''''''''''''''''

        Edit = MenuBar.addMenu(" Edit ")
        Edit.addAction(ITEM("Undo", "Ctrl+Z", "undo", self.proces, self))
        Edit.addAction(ITEM("Redo", "Ctrl+Shift+Z", "redo", self.proces, self))
        Edit.addAction(ITEM("Copy", "Ctrl+C", "copy", self.proces, self))
        Edit.addAction(ITEM(" Cut", "Ctrl+x", "cut", self.proces, self))
        Edit.addAction(ITEM(" Past", "Ctrl+v", "past", self.proces, self))
        Edit.addAction(ITEM(" Find", "Ctrl+f", "find", self.proces, self))
        Edit.addAction(ITEM(" Replace", "Ctrl+r", "replace", self.proces, self))
        Edit.addAction(ITEM(" Select All", "Ctrl+v", "select all", self.proces, self))
        # '''''''''''''''''''''''''''''''''''''''''''        '''''''''''''''''''''''''''''''''''''''
        Terminal = MenuBar.addMenu("Terminal")
        Terminal.addAction(ITEM("Editor", "Alt+E", "Editor", lambda: Editor.setVisible(True), self))

        # '''''''''''''''''''''''''''''''''''''''''''        '''''''''''''''''''''''''''''''''''''''

        window = MenuBar.addMenu("Window")
        window.addAction(
            ITEM("Full Screen", "Shift+Esc", "Full Screen", lambda: (self.showFullScreen(), MenuBar.setVisible(False)),
                 self))

        # '''''''''''''''''''''''''''''''''''''''''''        '''''''''''''''''''''''''''''''''''''''
        Help = MenuBar.addMenu(" Help")
        Help.addAction(ITEM("About", "Alt+A", "About", self.About, self))

        # ================================= Menu Bar Finished ==========================

        self.Tab = QTabWidget()
        self.Tab.setTabsClosable(True)
        self.Tab.tabCloseRequested.connect(lambda i: self.Tab.removeTab(i))
        Editor = EDITOR(TabWidget=self.Tab)
        Website = BROWSER()
        self.setCentralWidget(Website)
        self.addDockWidget(Qt.BottomDockWidgetArea, Editor)
        self.statusBar()

        self.WebSiteUpdate.connect(Website.Update)
        self.WebSiteReload.connect(Website.Reload)

    def proces(self):
        pass

    def About(self):
        pass

    def SaveAs(self):
        pass

    def Open(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "OpenFileName.....", "",
         "All file(*.php;*.html;*.css;*.js);;PHP Files (*.php);;HTML5 Files (*.html);;StyleSheet Files (*.css);;JavaScript Files (*.js)")
        if fileName:
            if os.path.splitext(fileName)[1] == '.html':
                HTML = HTML_EDITOR(self, fileName)
                with open(fileName, 'r') as f:
                    HTML.setPlainText(f.read())
                i = self.Tab.addTab(HTML, os.path.basename(fileName))
                self.Tab.setCurrentIndex(i)
            else:
                editor = TEXT_EDITOR(self, fileName)
                with open(fileName, 'r') as f:
                    editor.setPlainText(f.read())
                i = self.Tab.addTab(editor, os.path.basename(fileName))
                self.Tab.setCurrentIndex(i)

    def addTab(self, file):
        path = f'{pathlib.Path().absolute()}\\{file}'
        if os.path.splitext(path)[1] == ".html":
            HTML = HTML_EDITOR(self, path)
            HTML.insertPlainText('''<!DOCTYPE html>
        <html>
        <head>
        	<meta charset="utf-8">
        	<title> New html File</title>
        </head>
        <body>

        </body>
        </html>
                    ''')
            i = self.Tab.addTab(HTML, file)
            self.Tab.setCurrentIndex(i)
        else:
            Editor = TEXT_EDITOR(self, path)
            i = self.Tab.addTab(Editor, file)
            self.Tab.setCurrentIndex(i)


class EDITOR(QDockWidget):
    def __init__(self, TabWidget):
        super(EDITOR, self).__init__()
        self.setStyleSheet("""
        QDockWidget{
       color: red;
        }

        """)
        self.setMinimumHeight(250)
        self.setWindowTitle("Editor")
        self.setWidget(TabWidget)

    def closeEvent(self, event):
        event.ignore()
        if self.isFloating():
            self.setFloating(False)
        else:
            self.setVisible(False)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())
    except Exception:
       pass