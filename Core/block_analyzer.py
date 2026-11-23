import io
import tokenize


class BlockAnalyzer:
    HEADERS = {
        'def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try',
        'except', 'finally', 'with', 'match', 'case',
    }

    def __init__(self, document):
        self.structure = self.analyze_document(document)

    def analyze_document(self, document):
        return self.analyze_text(document.toRawText().replace('\u2029', '\n'))

    @classmethod
    def analyze_text(cls, text):
        lines = text.split('\n')
        structure = []
        for block_id, line in enumerate(lines):
            leading = line[:len(line) - len(line.lstrip(' \t\f'))]
            structure.append({
                'id': block_id,
                'indent': len(leading.expandtabs(8).rsplit('\f', 1)[-1]),
                'level': None,
                'is_opener': False,
            })

        suites = []
        statement = []
        pending = None
        depth_changes = {}
        scan_end = len(lines)

        def close_suite(end):
            suite = suites.pop()
            if suite is None:
                return
            start, body, _ = suite
            while end >= body:
                stripped = lines[end].lstrip()
                if stripped and (not stripped.startswith('#')
                                 or structure[end]['indent'] > structure[start]['indent']):
                    break
                end -= 1
            if end >= body:
                heading = lines[start]
                leading = heading[:len(heading) - len(heading.lstrip(' \t\f'))]
                structure[start].update(is_opener=True, body_start=body, end=end,
                                        leading=leading)

        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                kind, value, (row, _), _, _ = token
                if kind == tokenize.INDENT:
                    suites.append(pending)
                    depth_changes[row - 1] = len(suites)
                    pending = None
                elif kind == tokenize.DEDENT:
                    close_suite(min(row - 2, len(lines) - 1))
                    depth_changes[row - 1] = len(suites)
                elif kind == tokenize.NEWLINE:
                    pending = None
                    if statement and statement[-1].string == ':':
                        first = statement[0]
                        keyword = first.string
                        if keyword == 'async' and len(statement) > 2:
                            keyword = statement[1].string
                            if keyword not in {'def', 'for', 'with'}:
                                keyword = ''
                        if keyword == 'case' and (not suites or not suites[-1]
                                                   or suites[-1][2] != 'match'):
                            keyword = ''
                        if keyword in cls.HEADERS:
                            pending = (first.start[0] - 1, row, keyword)
                    statement.clear()
                elif kind not in (tokenize.NL, tokenize.COMMENT, tokenize.ENDMARKER):
                    pending = None
                    statement.append(token)
        except IndentationError as error:
            scan_end = error.lineno - 1
        except tokenize.TokenError as error:
            # An unfinished string or bracket can interrupt tokenizing while the user types.
            if error.args[0] == 'EOF in multi-line string':
                scan_end = error.args[1][0] - 1

        while suites:
            close_suite(min(scan_end, len(lines)) - 1)

        depth = 0
        parents = []
        for block_id, block in enumerate(structure):
            depth = depth_changes.get(block_id, depth)
            if depth or block['is_opener']:
                block['level'] = depth
            while parents and block_id > structure[parents[-1]]['end']:
                parents.pop()
            block['parent'] = parents[-1] if parents else None
            if block['is_opener']:
                parents.append(block_id)
        return structure
