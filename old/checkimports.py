#!/usr/bin/env python
'''Check and sort import statement from a python file '''

import re
import sys


class CheckImports(object):

    '''
    I can be used to check and sort import statement of a python file
    Please use sortImportGroups() method
    '''

    _regexImport = re.compile(r"^import\s+(.*)")
    _regexFromImport = re.compile(r"^from\s+([a-zA-Z0-9\._]+)\s+import\s+(.*)$")

    def __init__(self):
        self._previousLineString = None
        self._previousLineType = None
        self._writeError = True
        self.resetOrder()

    def printErrorMsg(self, filename, lineNb, errorMessage):
        ''' I print the error message following pylint convention'''
        if self._writeError:
            print ("%(filename)s:%(line_nb)s: %(error_msg)s" %
                   dict(filename=filename,
                        line_nb=lineNb,
                        error_msg=errorMessage))

    def isImportLine(self, line):
        '''I return True is the given line is an import statement, False otherwize'''
        return self._regexImport.match(line) or self._regexFromImport.match(line)

    def isBadLineFixable(self, line):
        '''I return True is the given line is an import line than I know how to split'''
        if self.isImportLine(line) and ',' in line:
            return True
        return False

    def analyzeLine(self, filename, line, lineNb):
        '''I look at the line and print all error I find'''
        res = True
        if self.isImportLine(line):
            if ';' in line:
                self.printErrorMsg(filename, lineNb,
                                   "multiple import statement on one line. "
                                   "Put each import on its own line.")
                res = False
            if ',' in line:
                self.printErrorMsg(filename, lineNb,
                                   "multiple module imported on one line. "
                                   "Please import each module on a single line.")
                res = False
            if '\\' in line:
                self.printErrorMsg(filename, lineNb,
                                   "new line character found. "
                                   "Please import each module on a single line")
            if '(' in line:
                self.printErrorMsg(filename, lineNb,
                                   "parenthesis character found. "
                                   "Please import each module on a single line")
                res = False
        return res

    def resetOrder(self):
        '''I reset the internal variables used to check the order of the lines'''
        self._previousLineString = None
        self._previousLineType = None

    def checkOrder(self, filename, line, lineNb):
        '''I check the given line is in the right order than the previous I was given'''
        line = line.partition("#")[0]
        line = line.rstrip()
        if not line:
            # changing group => reseting groups
            self.resetOrder()
            return True

        module = None
        import_match = self._regexImport.match(line)
        from_match = self._regexFromImport.match(line)

        if ((self._previousLineType == "import" and from_match is not None) or
                (self._previousLineType == "from" and import_match is not None)):
            self.printErrorMsg(filename, lineNb,
                               "Warning: mixing of 'import ...' and 'from ... import ...' "
                               "statements in the same group")

        if import_match is not None:
            module = import_match
            current_group_type = "import"
        elif from_match is not None:
            module = from_match
            current_group_type = "from"

        if not module:
            return True

        if not self._previousLineString:
            self._previousLineString = line
            self._previousLineType = current_group_type
            return True
        comp = self.compareImportLines(self._previousLineString, line)
        self._previousLineString = line
        self._previousLineType = current_group_type
        if comp > 0:
            self.printErrorMsg(filename, lineNb,
                               "Bad order for this import")
            return False
        else:
            return True

    def compareImportLines(self, importLine1, importLine2):
        '''
        I compare the two given lines, and return >0 if importLine1 is higher than importLine2,
        <0 if importline2 is higher than importLine1, and == 0 if both lines are identical

        Note: import lines will be placed becore from/import lines
        '''
        import_match1 = self._regexImport.match(importLine1)
        from_match1 = self._regexFromImport.match(importLine1)
        import_match2 = self._regexImport.match(importLine2)
        from_match2 = self._regexFromImport.match(importLine2)
        assert(import_match1 is not None or from_match1 is not None)
        assert(import_match2 is not None or from_match2 is not None)

        if ((import_match1 is not None) != (import_match2 is not None)):
            if import_match1:
                return -1
            else:
                return 1
        if importLine1 < importLine2:
            return -1
        elif importLine1 > importLine2:
            return 1
        else:
            return 0

    def checkData(self, filename, data):
        '''I perform an analysis of the files and print the error, without modifying the content'''
        res = True
        self.resetOrder()
        lines = data.split("\n")
        for cur_line_nb, line in enumerate(lines):
            if not self.analyzeLine(filename, line, cur_line_nb):
                res = False
            try:
                if not self.checkOrder(filename, line, cur_line_nb):
                    res = False
            except Exception:
                res = False
        return res

    def sortImportGroups(self, filename, data=None):
        '''
        I perform the analysis of the given file, print the error I find and try to split and
        sort the import statement
        '''
        lines = data.split("\n")
        res = True
        self.resetOrder()
        for cur_line_nb, line in enumerate(lines):
            if not self.analyzeLine(filename, line, cur_line_nb):
                if not self.isBadLineFixable(line):
                    res = False
            try:
                self.checkOrder(filename, line, cur_line_nb)
            except Exception:
                res = False
        if not res:
            return False, data

        # Check procedure is performed twice:
        # - the first time to check if no exception (= major error) does not
        #   occurs.
        # - if it's ok, we sort all the import within their group. Do
        #   do so, the check procedure will be used again.
        # So, disable the error printing to avoid not printing them twice.
        self._writeError = False
        self.resetOrder()

        # First split the import we can split
        newlines = []
        for line in lines:
            if self.isImportLine(line) and self.isBadLineFixable(line):
                match = self._regexFromImport.match(line)
                if match:
                    module = match.group(1)
                    imports = [s.strip() for s in match.group(2).split(",")]
                    for imp in imports:
                        newlines.append("from %s import %s" % (module, imp))
                    continue
            newlines.append(line)

        lines = newlines

        sorted_data = []
        current_group_start_line_nb = -1
        for cur_line_nb, line in enumerate(lines):
            if not line.strip() or not self.isImportLine(line):
                current_group_start_line_nb = -1
                sorted_data.append(line)
                self.resetOrder()
            else:
                if current_group_start_line_nb == -1:
                    current_group_start_line_nb = cur_line_nb
                    sorted_data.append(line)
                else:
                    comp = -1
                    if sorted_data:
                        comp = self.compareImportLines(sorted_data[-1], line)
                    if comp > 0:
                        i = len(sorted_data) - 1
                        while (i >= 0 and
                               i > current_group_start_line_nb):
                            i -= 1
                            if self.compareImportLines(sorted_data[i], line) < 0:
                                i += 1
                                break
                        sorted_data.insert(i, line)
                    else:
                        sorted_data.append(line)

        # reiterate line by line to split mixed groups
        splitted_groups_lines = []
        prev_import_line_type = ""
        for line in sorted_data:
            if not line.strip() or not self.isImportLine(line):
                splitted_groups_lines.append(line)
                prev_import_line_type = ""
            else:
                import_match = self._regexImport.match(line)
                from_match = self._regexFromImport.match(line)
                current_line_type = None
                if import_match is not None:
                    module = import_match
                    current_line_type = "import"
                elif from_match is not None:
                    module = from_match
                    current_line_type = "from"
                assert(current_line_type)
                if prev_import_line_type and current_line_type != prev_import_line_type:
                    splitted_groups_lines.append("")
                prev_import_line_type = current_line_type
                splitted_groups_lines.append(line)

        return True, "\n".join(splitted_groups_lines)


def main():
    '''I am the main method'''
    if len(sys.argv) != 2:
        print "usage: %s <python file>" % (sys.argv[0])
        sys.exit(1)

    filename = sys.argv[1]

    with open(filename, 'r') as filedesc:
        data = filedesc.read()
    res, content = CheckImports().sortImportGroups(filename, data)
    if not res:
        sys.exit(1)

    with open(filename, 'w') as filedesc:
        filedesc.write(content)
    if data != content:
        print "import successfully reordered for file: %s" % (filename)
    sys.exit(0)

if __name__ == "__main__":
    main()
