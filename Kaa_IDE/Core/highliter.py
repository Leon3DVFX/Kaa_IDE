from PySide6 import QtGui, QtCore
from Kaa_IDE.Core.loaders import jsonLoader

class EditorHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        #Загрузка опорного json
        elements = jsonLoader('python_keyword.json')
        self.string_ranges = []
        # Форматы
        self.keyWFormat = KeyWordFormat()  #keywords
        self.funcFormat = BuiltinsFormat()  #builtins
        self.magicFormat = MagicFormat()  #magics
        self.stdModFormat = StdModFormat()  #standart py modules
        self.commentFormat = CommentFormat()  #comments
        self.stringFormat = StringFormat()  #strings
        self.in_stringFormat = InStringFormat()  #strings_in
        self.numericFormat = NumericFormat()  #numeric
        self.customFuncFormat = CustomFuncFormat()  #custom functions
        #Элементы
        self.key = elements.get("keywords", [])
        self.func = elements.get("builtins", [])
        self.magic = elements.get("magic", [])
        self.modules = elements.get("modules", [])
        #Пред-компиляция REGEX
        #Строки
        self.str_patterns = [
            QtCore.QRegularExpression(r"(?P<prefix>r|f|fr|rf)?(?P<string>'(?:\\.|[^'])*')"),
            QtCore.QRegularExpression(r'(?P<prefix>r|f|fr|rf)?(?P<string>"(?:\\.|[^"])*")')
        ]
        self.str_regex_in1 = QtCore.QRegularExpression(r'(?<!\\)\{(.*?)\}')  #Для f-строк
        self.str_regex_in2 = QtCore.QRegularExpression(
            r'\\[abfnrtv\\\'"]|\\x[0-9A-Fa-f]{2}|\\u[0-9A-Fa-f]{4}|\\U[0-9A-Fa-f]{8}|\\N\{[A-Za-z0-9 '
            r'_-]+\}|\\[0-7]{1,3}')  #Для спец. символов
        #Ключевые слова
        self.key_pattern = []
        self.key_pattern.extend(self.get_pattern(self.key, self.keyWFormat))
        self.key_pattern.extend(self.get_pattern(self.func, self.funcFormat))
        self.key_pattern.extend(self.get_pattern(self.magic, self.magicFormat))
        self.key_pattern.extend(self.get_pattern(self.modules, self.stdModFormat))
        #Комментарии
        self.comment_pattern = QtCore.QRegularExpression(r'#.*')
        #Цифры int-float
        self.num_patterns = [
            QtCore.QRegularExpression(r'\b\d+\b'),  #Int
            QtCore.QRegularExpression(r'\b\d+\.\d*\b'),  #Float 123.456, 123. type
            QtCore.QRegularExpression(r'\B\.\d+\b'),  #Float .123 type
            QtCore.QRegularExpression(r'\b\d+[eE][+-]?\d+\b'),  #123e+-456 type
            QtCore.QRegularExpression(r'\b\d+\.\d*[eE][+-]?\d+\b'),  #123.123e+-456 type
            QtCore.QRegularExpression(r'\B\.\d+[eE][+-]?\d+\b'),  #.123e+-456 type
            QtCore.QRegularExpression(r'\b0x[0-9A-Fa-f]+\b'),  #hex: 0x12A3F (0x12af)
            QtCore.QRegularExpression(r'\b0o[0-7]+\b'),  #oct: 0o1234567
            QtCore.QRegularExpression(r'\b0b[01]+\b')  #bin: 0b010111
        ]
        #Кастомные функции
        self.custom_func_patterns = [
            QtCore.QRegularExpression(r'\b(def)\s+([A-Za-z_]\w*)\b'),  #для def
            QtCore.QRegularExpression(r'\b(class)\s+([A-Za-z_]\w*)\b')  #для class
        ]

    def get_pattern(self, e=None, f=None):
        keyword_pattern = []
        for keyword in e:
            pattern = QtCore.QRegularExpression(r'\b' + keyword + r'\b')
            keyword_pattern.append((pattern, f))
        return keyword_pattern

    def highlightBlock(self, text):
        self.string_ranges = []
        # 5. Цифры
        self.activateNum(text)
        # 4. Кастомные функции
        self.activateCustomFunctions(text)
        # 3. Ключевые слова
        self.activateKeyword(text, pat_and_formats=self.key_pattern)
        # 2. Строки
        self.activateStrings(text)
        # 1.Comments (самый верхний приоритет)
        comment_pattern = self.comment_pattern
        comment_it = comment_pattern.globalMatch(text)
        while comment_it.hasNext():
            match = comment_it.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self.commentFormat)

    # Подсветка по ключевым словам
    def activateKeyword(self, text=None, pat_and_formats=None):
        for p, f in pat_and_formats:
            expr = p
            it = expr.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, f)

    # Подсветка строк (ОДНОСТРОЧНЫЙ РЕЖИМ)
    def activateStrings(self, text):
        for pat in self.str_patterns:
            p_expr = pat
            it = p_expr.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                end = start + length
                self.string_ranges.append((start, end))
                self.setFormat(start, length, self.stringFormat)

                full_match = match.captured(0)
                # f-строки
                if full_match.startswith(('f', 'fr', 'rf')):
                    in_expr = self.str_regex_in1
                    in_it = in_expr.globalMatch(full_match)
                    while in_it.hasNext():
                        in_match = in_it.next()
                        in_start = start + in_match.capturedStart()
                        in_length = in_match.capturedLength()
                        self.setFormat(in_start, in_length, self.in_stringFormat)

                # Спецсимволы
                if not full_match.startswith(('r', 'rf', 'fr')):
                    in2_expr = self.str_regex_in2
                    in2_it = in2_expr.globalMatch(full_match)
                    while in2_it.hasNext():
                        in2_match = in2_it.next()
                        in2_start = start + in2_match.capturedStart()
                        in2_length = in2_match.capturedLength()
                        self.setFormat(in2_start, in2_length, self.in_stringFormat)

    # Подсветка цифр (int-float)
    def activateNum(self, text):
        for pat in self.num_patterns:
            p_expr = pat
            it = p_expr.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, self.numericFormat)

    #Подсветка своих функций
    def activateCustomFunctions(self, text):
        for pat in self.custom_func_patterns:
            p_expr = pat
            it = p_expr.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart(2)
                length = match.capturedLength(2)
                self.setFormat(start, length, self.customFuncFormat)


#Форматы символов для хайлайтера
class KeyWordFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#cb8964'))
        self.setFontWeight(QtGui.QFont.Weight.Bold)


class BuiltinsFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#a7a7e8'))


class MagicFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#e03792'))


class StdModFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#e0d57b'))


class CommentFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#787c83'))


class StringFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#84c567'))


class InStringFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#ed9838'))


class NumericFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#73cbd2'))


class CustomFuncFormat(QtGui.QTextCharFormat):
    def __init__(self):
        super().__init__()
        self.setForeground(QtGui.QColor('#58b9e9'))