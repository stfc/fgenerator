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

''' This module provides ... This wraps the f2py fortran parser to
    provide routines which can be used to generate fortran code. This library
    includes pytest tests. '''

from fparser.statements import Comment
from fparser.readfortran import FortranStringReader
from fparser.block_statements import Select
from fparser.statements import Case

from fgenerator.fparser_wrapper import OMPDirective

def index_of_object(alist, obj):
    '''Effectively implements list.index(obj) but returns the index of
    the first item in the list that *is* the supplied object (rather than
    comparing values) '''
    for idx, body in enumerate(alist):
        if body is obj:
            return idx
    raise Exception("Object {0} not found in list".format(str(obj)))


class BaseGen(object):
    ''' The base class for all classes that are responsible for generating
    distinct code elements (modules, subroutines, do loops etc.) '''
    def __init__(self, parent, root):
        self._parent = parent
        self._root = root
        self._children = []

    @property
    def parent(self):
        ''' Returns the parent of this object '''
        return self._parent

    @property
    def children(self):
        ''' Returns the list of children of this object '''
        return self._children

    @property
    def root(self):
        ''' Returns the root of the tree containing this object '''
        return self._root

    def add(self, new_object, position=None):
        '''Adds a new object to the tree. The actual position is determined by
        the position argument. Note, there are two trees, the first is
        the f2pygen object tree, the other is the f2py generated code
        tree. These are similar but different. At the moment we
        specify where to add things in terms of the f2pygen tree
        (which is a higher level api) but we also insert into the f2py
        tree at exactly the same location which needs to be sorted out
        at some point.

        '''

        # By default the position is 'append'. We set it up this way for
        # safety because in python, default arguments are instantiated
        # as objects at the time of definition. If this object is
        # subsequently modified then the value of the default argument
        # is modified for subsequent calls of this routine.
        if position is None:
            position = ["append"]

        if position[0] == "auto":
            raise Exception("Error: BaseGen:add: auto option must be "
                            "implemented by the sub class!")
        options = ["append", "first", "after", "before", "insert",
                   "before_index", "after_index"]
        if position[0] not in options:
            raise Exception("Error: BaseGen:add: supported positions are "
                            "{0} but found {1}".
                            format(str(options), position[0]))
        if position[0] == "append":
            self.root.content.append(new_object.root)
        elif position[0] == "first":
            self.root.content.insert(0, new_object.root)
        elif position[0] == "insert":
            index = position[1]
            self.root.content.insert(index, new_object.root)
        elif position[0] == "after":
            idx = index_of_object(self.root.content, position[1])
            self.root.content.insert(idx+1, new_object.root)
        elif position[0] == "after_index":
            self.root.content.insert(position[1]+1, new_object.root)
        elif position[0] == "before_index":
            self.root.content.insert(position[1], new_object.root)
        elif position[0] == "before":
            try:
                idx = index_of_object(self.root.content, position[1])
            except Exception as err:
                print str(err)
                raise RuntimeError(
                    "Failed to find supplied object in existing content - "
                    "is it a child of the parent?")
            self.root.content.insert(idx, new_object.root)
        else:
            raise Exception("Error: BaseGen:add: internal error, should "
                            "not get to here")
        self.children.append(new_object)

    def previous_loop(self):
        ''' Returns the *last* occurence of a loop in the list of
        siblings of this node '''
        from fparser.block_statements import Do
        for sibling in reversed(self.root.content):
            if isinstance(sibling, Do):
                return sibling
        raise RuntimeError("Error, no loop found - there is no previous loop")

    def last_declaration(self):
        '''Returns the *last* occurrence of a Declaration in the list of
            siblings of this node

        '''
        from fparser.typedecl_statements import TypeDeclarationStatement
        for sibling in reversed(self.root.content):
            if isinstance(sibling, TypeDeclarationStatement):
                return sibling

        raise RuntimeError("Error, no variable declarations found")

    def start_parent_loop(self, debug=False):
        ''' Searches for the outer-most loop containing this object. Returns
        the index of that line in the content of the parent. '''
        from fparser.block_statements import Do
        if debug:
            print "Entered before_parent_loop"
            print "The type of the current node is {0}".format(
                str(type(self.root)))
            print ("If the current node is a Do loop then move up to the "
                   "top of the do loop nest")

        # First off, check that we do actually have an enclosing Do loop
        current = self.root
        while not isinstance(current, Do) and getattr(current, 'parent', None):
            current = current.parent
        if not isinstance(current, Do):
            raise RuntimeError("This node has no enclosing Do loop")

        current = self.root
        local_current = self
        while isinstance(current.parent, Do):
            if debug:
                print "Parent is a do loop so moving to the parent"
            current = current.parent
            local_current = local_current.parent
        if debug:
            print "The type of the current node is now " + str(type(current))
            print "The type of parent is " + str(type(current.parent))
            print "Finding the loops position in its parent ..."
        index = current.parent.content.index(current)
        if debug:
            print "The loop's index is ", index
        parent = current.parent
        local_current = local_current.parent
        if debug:
            print "The type of the object at the index is " + \
                str(type(parent.content[index]))
            print "If preceding node is a directive then move back one"
        if index == 0:
            if debug:
                print "current index is 0 so finish"
        elif isinstance(parent.content[index-1], OMPDirective):
            if debug:
                print (
                    "preceding node is a directive so find out what type ...\n"
                    "type is {0}\ndirective is {1}".
                    format(parent.content[index-1].position,
                           str(parent.content[index-1])))
            if parent.content[index-1].position == "begin":
                if debug:
                    print "type of directive is begin so move back one"
                index -= 1
            else:
                if debug:
                    print "directive type is not begin so finish"
        else:
            if debug:
                print "preceding node is not a directive so finish"
        if debug:
            print "type of final location ", type(parent.content[index])
            print "code for final location ", str(parent.content[index])
        return local_current, parent.content[index]


