# Author R. Ford STFC Daresbury Lab

'''This module provides routines to modify an existing fparser
tree. We are currently limited to adding a use statement as that is
all that has been required so far.'''

from fparser.readfortran import FortranStringReader
from fparser.block_statements import Use
import fparser

def adduse(name, parent, only=False, funcnames=None):
    '''Adds a use statement with the specified name to the supplied
    object.  This routine is required when modifying an existing
    fparser AST. '''

    reader = FortranStringReader("use kern,only : func1_kern=>func1")
    reader.set_mode(True, True)  # free form, strict
    myline = reader.next()

    # find an appropriate place to add in our use statement
    while not (isinstance(parent, fparser.block_statements.Program) or
               isinstance(parent, fparser.block_statements.Module) or
               isinstance(parent, fparser.block_statements.Subroutine)):
        parent = parent.parent
    use = Use(parent, myline)
    use.name = name
    use.isonly = only
    if funcnames is None:
        funcnames = []
        use.isonly = False
    use.items = funcnames

    parent.content.insert(0, use)
    return use
