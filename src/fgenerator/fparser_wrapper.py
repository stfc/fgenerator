# BSD 3-Clause License
#
# Copyright (c) 2017, Science and Technology Facilities Council
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Author R. Ford STFC Daresbury Lab
#
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
