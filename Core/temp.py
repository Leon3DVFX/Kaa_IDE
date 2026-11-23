import json
import logging
import os
import re
from importlib import resources

from PySide6 import QtCore

temp_dir = str(resources.files('Kaa_IDE.Core').joinpath('temp'))
logger = logging.getLogger(__name__)

SESSION_FORMAT = 'Kaa_IDE'
SESSION_VERSION = 1
BOOKMARK_COLOR_COUNT = 6
QT_INT_MAX = 2**31 - 1
QT_WIDGET_MAX_SIZE = 16777215
SESSION_ERRORS = (OSError, ValueError, RecursionError)


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, lower, upper):
    return type(value) is int and lower <= value <= upper


def _keys(value, required, optional=()):
    return isinstance(value, dict) and required <= value.keys() <= required.union(optional)


def _validate_session(session):
    _check(_keys(session, {'format', 'version', 'tabs'}, {'window'}), 'Invalid session header.')
    _check(session['format'] == SESSION_FORMAT, 'Unknown session format.')
    _check(_integer(session['version'], SESSION_VERSION, SESSION_VERSION),
           'Unsupported session version.')

    tabs = session['tabs']
    _check(isinstance(tabs, list) and tabs, 'A session must contain at least one tab.')
    for index, tab in enumerate(tabs, 1):
        _check(_keys(tab, {'name', 'text', 'cursor', 'bookmarks', 'folds'}),
               f'Invalid structure in tab {index}.')
        _check(isinstance(tab['name'], str) and isinstance(tab['text'], str),
               f'Invalid name or text in tab {index}.')
        tab['name'].encode('utf-8')
        # QTextDocument represents CRLF, CR and paragraph separators as block boundaries.
        code = tab['text'].replace('\r\n', '\n').replace('\r', '\n').replace('\u2029', '\n')
        tab['text'] = code
        last_cursor = min(len(code.encode('utf-16-le')) // 2, QT_INT_MAX - 1)
        _check(_integer(tab['cursor'], 0, last_cursor), f'Invalid cursor in tab {index}.')

        last_line = code.count('\n')
        bookmarks = tab['bookmarks']
        _check(isinstance(bookmarks, list), f'Invalid bookmarks in tab {index}.')
        for bookmark in bookmarks:
            _check(isinstance(bookmark, list) and len(bookmark) == 2
                   and _integer(bookmark[0], 0, last_line)
                   and _integer(bookmark[1], 0, BOOKMARK_COLOR_COUNT - 1),
                   f'Invalid bookmark in tab {index}.')

        folds = tab['folds']
        _check(isinstance(folds, list), f'Invalid folds in tab {index}.')
        for fold in folds:
            _check(isinstance(fold, list) and len(fold) == 2
                   and _integer(fold[0], 0, last_line) and isinstance(fold[1], list),
                   f'Invalid fold in tab {index}.')
            _check(all(_integer(line, fold[0] + 1, last_line) for line in fold[1]),
                   f'Invalid folded lines in tab {index}.')

    if 'window' in session:
        window = session['window']
        _check(_keys(window, {'x', 'y', 'width', 'height', 'work_dir'}),
               'Invalid window settings.')
        for axis in ('x', 'y'):
            _check(_integer(window[axis], -QT_INT_MAX - 1, QT_INT_MAX),
                   f'Invalid window coordinate {axis}.')
        for dimension in ('width', 'height'):
            _check(_integer(window[dimension], 1, QT_WIDGET_MAX_SIZE),
                   f'Invalid window {dimension}.')
        directory = window['work_dir']
        _check(isinstance(directory, str) and directory and '\0' not in directory,
               'Invalid working directory.')
        directory.encode('utf-8')
    return session


def _legacy_line(stream):
    line = stream.readline()
    return line.removesuffix(b'\n').removesuffix(b'\r') if line else None


def _legacy_tab_name(stream, index):
    if _legacy_line(stream) != f'<index> = {index}'.encode('ascii'):
        return None
    name = _legacy_line(stream)
    cursor = _legacy_line(stream)
    if (name is not None and name.startswith(b'<win_name> = ')
            and cursor is not None and cursor.startswith(b'<cursor_position> = ')
            and _legacy_line(stream) == b'<text_start>'):
        return name.removeprefix(b'<win_name> = ')
    return None


def _read_legacy(stream):
    # Only the old framing is read. Values outside the tab name and text are ignored.
    count = re.fullmatch(rb'<wins_count> = ([0-9]+)', _legacy_line(stream) or b'')
    _check(count is not None and int(count[1]) > 0, 'Invalid legacy tab count.')
    tab_count = int(count[1])
    while True:
        offset = stream.tell()
        header = _legacy_line(stream)
        if header is None or not header.startswith((
            b'<WORK_DIRECTORY> = ', b'<X_POS> = ', b'<Y_POS> = ',
            b'<WIDTH> = ', b'<HEIGHT> = ',
        )):
            stream.seek(offset)
            break

    tabs = []
    for index in range(tab_count):
        name = _legacy_tab_name(stream, index)
        _check(name is not None, 'Invalid legacy tab header.')

        code_lines = []
        while (line := _legacy_line(stream)) is not None:
            if line == b'<text_end>':
                offset = stream.tell()
                following = _legacy_line(stream)
                if following is None or following in (
                    b'<PICKLE_DATA_BOOKMARKS>', b'<PICKLE_DATA_FOLDING>',
                ):
                    _check(index + 1 == tab_count, 'Invalid legacy tab count.')
                    break
                stream.seek(offset)
                if _legacy_tab_name(stream, index + 1) is not None:
                    _check(index + 1 < tab_count, 'Invalid legacy tab count.')
                    stream.seek(offset)
                    break
                stream.seek(offset)
            code_lines.append(line)
        else:
            raise ValueError('Missing legacy tab closing marker.')

        tabs.append({
            'name': name.decode('utf-8'),
            'text': b'\n'.join(code_lines).decode('utf-8'),
            'cursor': 0, 'bookmarks': [], 'folds': [],
        })

    return {'format': SESSION_FORMAT, 'version': SESSION_VERSION, 'tabs': tabs}


def _read_session(path):
    legacy_prefix = b'<wins_count> = '
    with open(path, 'rb') as stream:
        if stream.peek(len(legacy_prefix)).startswith(legacy_prefix):
            return _validate_session(_read_legacy(stream))
        return _validate_session(json.loads(stream.read().decode('utf-8-sig')))


def _save_session(path, session):
    data = json.dumps(_validate_session(session), ensure_ascii=False).encode('utf-8')
    file = QtCore.QSaveFile(os.fspath(path))
    if not file.open(QtCore.QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(file.errorString())
    if file.write(data) != len(data):
        message = file.errorString()
        file.cancelWriting()
        raise OSError(message)
    if not file.commit():
        raise OSError(file.errorString())


def _snapshot(mdi_area):
    tabs = []
    for subwindow in mdi_area.subWindowList():
        editor = subwindow.widget().editor
        gutter = editor.line_number_area
        last_line = editor.blockCount() - 1
        # Editing can leave stale line numbers in a fold's list of hidden blocks.
        folds = [
            [opener, [line for line in hidden if opener < line <= last_line]]
            for opener, hidden in gutter.folding_data
            if 0 <= opener <= last_line
        ]
        tabs.append({
            'name': subwindow.windowTitle(),
            'text': editor.document().toRawText().replace('\u2029', '\n'),
            'cursor': editor.textCursor().position(),
            'bookmarks': gutter.bookmark_data,
            'folds': folds,
        })
    return {'format': SESSION_FORMAT, 'version': SESSION_VERSION, 'tabs': tabs}


class TempSystem:
    def __init__(self):
        self.x = self.y = 0
        self.width, self.height = 400, 600
        self.work_dir = os.getcwd()

    def save_temp_file(self, mdi_area):
        parent = mdi_area.parent()
        launcher = parent.parent() if parent else None
        position = launcher.pos() if launcher else parent.pos() if parent else mdi_area.pos()
        size = parent.size() if parent else mdi_area.size()
        session = _snapshot(mdi_area)
        session['window'] = {
            'x': position.x(), 'y': position.y(), 'width': size.width(), 'height': size.height(),
            'work_dir': self.work_dir,
        }
        try:
            os.makedirs(temp_dir, exist_ok=True)
            _save_session(os.path.join(temp_dir, 'main_temp.kaa'), session)
        except SESSION_ERRORS as error:
            logger.warning('Could not save the Kaa autosession: %s', error)

    def load_temp_file(self, mdi_area):
        try:
            session = _read_session(os.path.join(temp_dir, 'main_temp.kaa'))
        except FileNotFoundError:
            return
        except SESSION_ERRORS as error:
            logger.warning('Could not load the Kaa autosession: %s', error)
            return
        if 'window' in session:
            window = session['window']
            self.x, self.y = window['x'], window['y']
            self.width, self.height = window['width'], window['height']
            self.work_dir = window['work_dir']
        mdi_area.restore_tabs(session['tabs'])

    def save_kaa_file(self, mdi_area, path):
        _save_session(path, _snapshot(mdi_area))

    def load_kaa_file(self, mdi_area, path):
        session = _read_session(path)
        self.work_dir = os.path.dirname(os.path.abspath(path))
        mdi_area.restore_tabs(session['tabs'])
        mdi_area.save_session()

    def save_py_file(self, mdi_area=None, path=None):
        with open(path, 'w+', encoding='utf-8') as file:
            editor = mdi_area.activeSubWindow().widget().editor
            text = editor.toPlainText()
            file.write(text)

    def load_py_files(self, mdi_area=None, paths=None):
        for path in paths:
            text = ''
            # Поиск имени для нового таба
            dirs = path.split('/')
            f = dirs[-1]
            n = f.split('.')
            name = n[0]
            # Чтение текста из файла
            with open(path, 'r', encoding='utf-8') as file:
                text = file.read()

            mdi_area.new_tab()
            editor = mdi_area.activeSubWindow().widget().editor
            mdi_area.activeSubWindow().setWindowTitle(name)
            editor.setPlainText(text)
