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
