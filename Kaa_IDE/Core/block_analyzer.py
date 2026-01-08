class BlockAnalyzer:
    def __init__(self, document, prev_structure = None):
        self.document = document
        self.prev_structure = prev_structure
        self.structure = self.analyze_document(self.document)

    def analyze_document(self, document):
        block = document.firstBlock()
        structure = []

        while block.isValid():
            text = block.text()
            indent = len(text) - len(text.lstrip())
            block_id = block.blockNumber()
            is_opener = False
            level = None
            # Условия
            con1 = text.strip().endswith(':')
            con2 = text.strip().startswith('def')
            con3 = text.strip().startswith('if')
            con4 = text.strip().startswith('elif')
            con5 = text.strip().startswith('else')
            con6 = text.strip().startswith('class')

            # Проверяем свернут ли стартер

            if (con1 or con2 or con3 or con4 or con5 or con6) and indent == 0:  # Это самый старший блок - начало
                is_opener = True
                level = 0

            elif (con1 or con2 or con3 or con4 or con5 or con6) and indent > 0:  # Это вложенный блок (или ошибка отступа)
                is_opener = True
                prev = structure[-1]
                if indent < prev['indent']:
                    level = prev['level']
                elif indent == prev['indent']:
                    level = (prev['level'] or 0) + 1
                else:
                    level = (prev['level'] or 0) + 1

            elif not (con1 or con2 or con3 or con4 or con5 or con6) and indent > 0:  # Любой внутри-блоковый текст
                if structure:
                    level = structure[-1]['level']
                else:
                    indent = 0
                    level = None

            elif not (con1 or con2 or con3 or con4 or con5 or con6) and indent == 0:  # Любой вне-блоковый текст верхнего уровня
                is_opener = False
                level = None

            if text.strip() == '':  # Пустая строка
                if structure:  # Проверяем что structure не пустой
                    # Берем уровень и отступ последнего блока
                    prev = structure[-1]
                    level = prev['level']
                    indent = prev['indent']

                else:
                    level = None
                    indent = 0

            structure.append({
                'id': block_id,
                'indent': indent,
                'level': level,
                'is_opener': is_opener
            })

            block = block.next()

        return structure