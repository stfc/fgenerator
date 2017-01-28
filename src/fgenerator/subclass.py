# Author R. Ford STFC Daresbury Lab

''' Fortran code-generation library. This wraps the f2py fortran parser to
    provide routines which can be used to generate fortran code. This library
    includes pytest tests. '''

from fparser.statements import Comment
from fparser.readfortran import FortranStringReader
from fparser.block_statements import Select
from fparser.statements import Case


class OMPDirective(Comment):
    ''' Subclass f2py comment for OpenMP directives so we can
        reason about them when walking the tree '''
    def __init__(self, root, line, position, dir_type):
        self._types = ["parallel do", "parallel", "do", "master"]
        self._positions = ["begin", "end"]
        if dir_type not in self._types:
            raise RuntimeError("Error, unrecognised directive type '{0}'. "
                               "Should be one of {1}".
                               format(dir_type, self._types))
        if position not in self._positions:
            raise RuntimeError("Error, unrecognised position '{0}'. "
                               "Should be one of {1}".
                               format(position, self._positions))
        self._my_type = dir_type
        self._position = position
        Comment.__init__(self, root, line)

    @property
    def type(self):
        ''' Returns the type of this OMP Directive (one of 'parallel do',
        'parallel' or 'do') '''
        return self._my_type

    @property
    def position(self):
        ''' Returns the position of this OMP Directive ('begin' or 'end') '''
        return self._position
