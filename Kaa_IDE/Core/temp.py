import os, pickle, base64
from importlib import resources
from PySide6 import QtCore

temp_dir = str(resources.files('Kaa_IDE.Core').joinpath('temp'))


class TempSystem:
    def __init__(self, parent=None):
        self.pickle_separator_folding = '<PICKLE_DATA_FOLDING>\n'
        self.pickle_separator_bookmarks = '<PICKLE_DATA_BOOKMARKS>\n'
        self.fold_obj = None
        self.mdi = parent
        self.work_dir = os.getcwd()

        #Предкомпиляция регулярок
        self.pattern_wins_count = QtCore.QRegularExpression(r'<wins_count> = (\d+)')
        self.pattern_x_pos = QtCore.QRegularExpression(r'<X_POS> = (\d+)')
        self.pattern_y_pos = QtCore.QRegularExpression(r'<Y_POS> = (\d+)')
        self.pattern_width = QtCore.QRegularExpression(r'<WIDTH> = (\d+)')
        self.pattern_height = QtCore.QRegularExpression(r'<HEIGHT> = (\d+)')
        self.pattern_work_dir = QtCore.QRegularExpression(r'<WORK_DIRECTORY> = (.+)')

        # Пробуем восстановить позицию по файлу (если он есть)
        try:
            with open(temp_dir + r'\main_temp.kaa', 'r', encoding='utf-8') as file:
                self.last_loaded = file.read()
            mx = self.pattern_x_pos.match(self.last_loaded)
            self.x = int(mx.captured(1))
            if self.x < 0:
                self.x = 0
            my = self.pattern_y_pos.match(self.last_loaded)
            self.y = int(my.captured(1))
            if self.y < 0:
                self.y = 0
            mw = self.pattern_width.match(self.last_loaded)
            self.width = int(mw.captured(1))
            mh = self.pattern_height.match(self.last_loaded)
            self.height = int(mh.captured(1))
            wd = self.pattern_work_dir.match(self.last_loaded)
            self.work_dir = wd.captured(1)
        # Если нету - создадим
        except FileNotFoundError:
            self.last_loaded = None
            self.x = 0
            self.y = 0
            self.width = 400
            self.height = 600

        # Пооконный парсер (регулярка)
        self.pattern_block = QtCore.QRegularExpression(
            r'<index> = (\d+)\s*<win_name> = (\S*)\s*<cursor_position> = (\d+)\s*',
            QtCore.QRegularExpression.PatternOption.DotMatchesEverythingOption
        )
        self.pattern_text = QtCore.QRegularExpression(
            r'<text_start>\s(.*?\s*)\s<text_end>',
            QtCore.QRegularExpression.PatternOption.DotMatchesEverythingOption
        )

        self.pattern_bookmarks = QtCore.QRegularExpression(
            r'<PICKLE_DATA_BOOKMARKS>\s(\S+)\s',
            QtCore.QRegularExpression.PatternOption.DotMatchesEverythingOption
        )

    def save_temp_file(self, mdi_area=None):
        # Создание папки если не существует
        os.makedirs(temp_dir, exist_ok=True)
        # Запись temp файла
        with open(temp_dir + r'\main_temp.kaa', 'w+', encoding='utf-8') as file:
            file.write(f'<wins_count> = {len(mdi_area.subWindowList())}\n')
            file.write(f'<WORK_DIRECTORY> = {self.work_dir}\n')
            file.write(f'<X_POS> = {mdi_area.parent().parent().pos().x()}\n')
            file.write(f'<Y_POS> = {mdi_area.parent().parent().pos().y()}\n')
            file.write(f'<WIDTH> = {mdi_area.parent().width()}\n')
            file.write(f'<HEIGHT> = {mdi_area.parent().height()}\n')

        with open(temp_dir + r'\main_temp.kaa', 'a+', encoding='utf-8') as file:
            for i, subwindow in enumerate(mdi_area.subWindowList()):
                file.write(f'<index> = {i}\n')
                file.write(f'<win_name> = {subwindow.windowTitle()}\n')
                text = subwindow.widget().editor.toPlainText()
                cursor_position = subwindow.widget().editor.textCursor().position()
                file.write(f'<cursor_position> = {cursor_position}\n')
                file.write('<text_start>\n')
                file.write(text + '\n')
                file.write('<text_end>\n')
        # Пиклы с данными фолдинга
        all_folds = []
        all_books = []
        with open(temp_dir + r'\main_temp.kaa', 'a+', encoding='utf-8') as file:
            subwindows = mdi_area.subWindowList()
            for subwindow in subwindows:
                fold_data = subwindow.widget().editor.line_number_area.folding_data
                book_data = subwindow.widget().editor.line_number_area.bookmark_data
                if not fold_data:
                    fold_data = None
                all_folds.append(fold_data)
                if not book_data:
                    book_data = None
                all_books.append(book_data)

            pickled_folds = pickle.dumps(all_folds)
            encoded_folds = base64.b64encode(pickled_folds).decode('utf-8')

            pickled_books = pickle.dumps(all_books)
            encoded_books = base64.b64encode(pickled_books).decode('utf-8') + '\n'
            file.write(self.pickle_separator_bookmarks)
            file.write(encoded_books)
            file.write(self.pickle_separator_folding)
            file.write(encoded_folds)

    def load_temp_file(self, mdi_area=None):
        # Создание папки если не существует
        os.makedirs(temp_dir, exist_ok=True)
        #Проверка наличия файлов в папке temp (пока что этого будет достаточно)
        if not len(os.listdir(temp_dir)):
            return

        with open(temp_dir + r'\main_temp.kaa', 'r', encoding='utf-8') as file:
            self.last_loaded = file.read()

        # Парсинг (общее число окон для создания)
        num_expr = self.pattern_wins_count
        it = num_expr.globalMatch(self.last_loaded)
        n = 0
        while it.hasNext():
            match = it.next()
            n = int(match.captured(1))
        # Удаление всех предыдущих окон
        mdi_area.closeAllSubWindows()
        # Воссоздание численности окон
        for i in range(n - 1):
            mdi_area.new_tab()
        # Парсинг и восстановление блоков
        it_wins = self.pattern_block.globalMatch(self.last_loaded)
        it_text = self.pattern_text.globalMatch(self.last_loaded)
        while it_wins.hasNext() and it_text.hasNext():
            p_match = it_wins.next()
            t_match = it_text.next()
            index = int(p_match.captured(1))
            win_name = str(p_match.captured(2)).strip()
            cursor_pos = int(p_match.captured(3))
            text = t_match.captured(1)
            # Восстановление окна по индексу
            mdi_area.restore_window(index, text, cursor_pos, win_name)
        #Загрузка пиклов
        # Буки + подсветка
        all_books = None
        book_expr = self.pattern_bookmarks
        book_match = book_expr.match(self.last_loaded)
        if book_match.hasMatch():
            pickled_books = book_match.captured(1)
            decoded_books = base64.b64decode(pickled_books)
            try:
                all_books = pickle.loads(decoded_books)
            except Exception:
                all_books = None
        if all_books:
            subwindows = mdi_area.subWindowList()
            for i, subwindow in enumerate(subwindows):
                book_data = all_books[i]

                if not book_data:
                    continue
                lna = subwindow.widget().editor.line_number_area
                lna.calculate_books(book_data)

        # Фолдеры
        all_folds = None
        if self.pickle_separator_folding in self.last_loaded:
            parts = self.last_loaded.split(self.pickle_separator_folding)
            if len(parts) > 1:
                pickled = parts[1]
                decoded = base64.b64decode(pickled)
                try:
                    all_folds = pickle.loads(decoded)
                except Exception:
                    all_folds = None
        if all_folds:
            subwindows = mdi_area.subWindowList()
            for i, subwindow in enumerate(subwindows):
                fold_data = all_folds[i]

                if not fold_data:
                    continue

                lna = subwindow.widget().editor.line_number_area
                lna.calculate_folding(fold_data)

    # Сохранение в Py файлы
    def save_py_file(self, mdi_area=None, path=None):
        with open(path, 'w+', encoding='utf-8') as file:
            editor = mdi_area.activeSubWindow().widget().editor
            text = editor.toPlainText()
            file.write(text)

    # Сохранение в фаил полной версии
    def save_kaa_file(self, mdi_area=None, path=None):
        # Запись kaa файла
        with open(path, 'w+', encoding='utf-8') as file:
            file.write(f'<wins_count> = {len(mdi_area.subWindowList())}\n')

        with open(path, 'a+', encoding='utf-8') as file:
            for i, subwindow in enumerate(mdi_area.subWindowList()):
                file.write(f'<index> = {i}\n')
                file.write(f'<win_name> = {subwindow.windowTitle()}\n')
                text = subwindow.widget().editor.toPlainText()
                cursor_position = subwindow.widget().editor.textCursor().position()
                file.write(f'<cursor_position> = {cursor_position}\n')
                file.write('<text_start>\n')
                file.write(text + '\n')
                file.write('<text_end>\n')
        # Пиклы с данными фолдинга
        all_folds = []
        all_books = []
        with open(path, 'a+', encoding='utf-8') as file:
            subwindows = mdi_area.subWindowList()
            for subwindow in subwindows:
                fold_data = subwindow.widget().editor.line_number_area.folding_data
                book_data = subwindow.widget().editor.line_number_area.bookmark_data
                if not fold_data:
                    fold_data = None
                all_folds.append(fold_data)
                if not book_data:
                    book_data = None
                all_books.append(book_data)

            pickled_folds = pickle.dumps(all_folds)
            encoded_folds = base64.b64encode(pickled_folds).decode('utf-8')

            pickled_books = pickle.dumps(all_books)
            encoded_books = base64.b64encode(pickled_books).decode('utf-8') + '\n'
            file.write(self.pickle_separator_bookmarks)
            file.write(encoded_books)
            file.write(self.pickle_separator_folding)
            file.write(encoded_folds)

    # Загрузка полной версии из файла
    def load_kaa_file(self, mdi_area=None, path=None):
        # 1. Удаление всех предыдущих окон
        mdi_area.closeAllSubWindows()
        # 2. Чтение файла
        with open(path, 'r', encoding='utf-8') as file:
            self.last_loaded = file.read()
        # 3. Отложенное восстановление окон
        QtCore.QTimer.singleShot(
            0,
            lambda: self._restore_windows_phase(mdi_area)
        )

    # Восстановление окон под таймер (смена фазы для MDI)
    def _restore_windows_phase(self, mdi_area):
        # Парсинг (общее число окон для создания)
        it = self.pattern_wins_count.globalMatch(self.last_loaded)
        n = 0
        while it.hasNext():
            match = it.next()
            n = int(match.captured(1))

        # Воссоздание численности окон
        for i in range(n - 1):
            mdi_area.new_tab()

        # Парсинг и восстановление блоков
        it_wins = self.pattern_block.globalMatch(self.last_loaded)
        it_text = self.pattern_text.globalMatch(self.last_loaded)
        while it_wins.hasNext() and it_text.hasNext():
            p_match = it_wins.next()
            t_match = it_text.next()
            index = int(p_match.captured(1))
            win_name = str(p_match.captured(2)).strip()
            cursor_pos = int(p_match.captured(3))
            text = t_match.captured(1)
            # Восстановление окна по индексу
            mdi_area.restore_window(index, text, cursor_pos, win_name)
        # Фаза восстановления бук-фолдеров
        QtCore.QTimer.singleShot(
            0,
            lambda: self._restore_meta_phase(mdi_area)
        )

    # Восстановление бук-фолдеров (смена фазы под MDI)
    def _restore_meta_phase(self, mdi_area):
        # Загрузка пиклов
        # Буки + подсветка
        all_books = None
        book_expr = self.pattern_bookmarks
        book_match = book_expr.match(self.last_loaded)
        if book_match.hasMatch():
            pickled_books = book_match.captured(1)
            decoded_books = base64.b64decode(pickled_books)
            try:
                all_books = pickle.loads(decoded_books)
            except Exception:
                all_books = None
        if all_books:
            subwindows = mdi_area.subWindowList()
            for i, subwindow in enumerate(subwindows):
                book_data = all_books[i]

                if not book_data:
                    continue
                lna = subwindow.widget().editor.line_number_area
                lna.calculate_books(book_data)

        # Фолдеры
        all_folds = None
        if self.pickle_separator_folding in self.last_loaded:
            parts = self.last_loaded.split(self.pickle_separator_folding)
            if len(parts) > 1:
                pickled = parts[1]
                decoded = base64.b64decode(pickled)
                try:
                    all_folds = pickle.loads(decoded)
                except Exception:
                    all_folds = None
        if all_folds:
            subwindows = mdi_area.subWindowList()
            for i, subwindow in enumerate(subwindows):
                fold_data = all_folds[i]

                if not fold_data:
                    continue

                lna = subwindow.widget().editor.line_number_area
                lna.calculate_folding(fold_data)

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


if __name__ == '__main__':
    print(temp_dir)
