class InsertOp:
    def __init__(self, line, col, char):
        self.line = line
        self.col = col
        self.char = char
        
    def transform_against(self, other):
        line, col = self.line, self.col

        if isinstance(other, InsertOp):
            if other.line == line:
                if other.col < col or (other.col == col and other.char < self.char):
                    col += 1
            elif other.char == '\n':
                if other.line < line:
                    line += 1
                elif other.line == line and other.col <= col:
                    line += 1
                    col -= other.col

        elif isinstance(other, DeleteOp):
            if other.line == line:
                if other.col < col:
                    col -= 1
            if other.line < line:
                line -= 1

        return InsertOp(line, col, self.char)


    def apply(self, lines):
        while self.line >= len(lines):
            lines.append("")

        line_text = lines[self.line]
        col = min(self.col, len(line_text))  # use local variable instead

        if self.char == '\n':
            before = line_text[:col]
            after = line_text[col:]
            lines[self.line] = before
            lines.insert(self.line + 1, after)
        else:
            lines[self.line] = line_text[:col] + self.char + line_text[col:]

        return lines



class DeleteOp:
    def __init__(self, line, col):
        self.line = line
        self.col = col

    def transform_against(self, other):
        line, col = self.line, self.col

        if isinstance(other, InsertOp):
            if other.line == line:
                if other.col < col:
                    col += 1
            elif other.line < line and other.char == '\n':
                line += 1
            elif other.line == line and other.char == '\n' and other.col <= col:
                line += 1
                col -= other.col

        elif isinstance(other, DeleteOp):
            if other.line == line:
                if other.col < col:
                    col -= 1
                elif other.col == col:
                    return None
            elif other.line < line:
                line -= 1

        return DeleteOp(line, col)




    def apply(self, lines):
        if self.line >= len(lines):
            return lines

        line_text = lines[self.line]
        col = self.col

        if col < len(line_text):
            lines[self.line] = line_text[:col] + line_text[col + 1:]
        elif col == len(line_text) and self.line + 1 < len(lines):
            lines[self.line] += lines[self.line + 1]
            del lines[self.line + 1]

        return lines

