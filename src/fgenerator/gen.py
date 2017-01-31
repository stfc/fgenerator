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
'''This module provides classes to generate fortran code in a
relatively high level way. Under the hood it uses fparser to generate
the code.'''

from fparser.statements import Comment
from fparser.readfortran import FortranStringReader
from fparser.block_statements import Select
from fparser.statements import Case

from fgenerator.fparser_wrapper import OMPDirective

# Module-wide utility methods

def bubble_up_type(obj):
    ''' Returns True if the supplied object is of a type which must be
    bubbled-up (from within e.g. DO loops) '''
    return (isinstance(obj, UseGen) or
            isinstance(obj, DeclGen) or
            isinstance(obj, TypeDeclGen))

from fgenerator.base import BaseGen

class ProgUnitGen(BaseGen):
    ''' Functionality relevant to program units (currently modules,
    subroutines)'''
    def __init__(self, parent, sub):
        BaseGen.__init__(self, parent, sub)

    def add(self, content, position=None, bubble_up=False):
        '''Specialise the add method to provide module and subroutine
           specific intelligent adding of use statements, implicit
           none statements and declarations if the position argument
           is set to auto (which is the default)'''

        # By default the position is 'auto'. We set it up this way for
        # safety because in python, default arguments are instantiated
        # as objects at the time of definition. If this object is
        # subsequently modified then the value of the default argument
        # is modified for subsequent calls of this routine.
        if position is None:
            position = ["auto"]

        # For an object to be added to another we require that they
        # share a common ancestor. This means that the added object must
        # have the current object or one of its ancestors as an ancestor.
        # Loop over the ancestors of this object (starting with itself)
        self_ancestor = self.root
        while self_ancestor:
            # Loop over the ancestors of the object being added
            obj_parent = content.root.parent
            while (obj_parent != self_ancestor and
                   getattr(obj_parent, 'parent', None)):
                obj_parent = obj_parent.parent
            if obj_parent == self_ancestor:
                break
            # Object being added is not an ancestor of the current
            # self_ancestor so move one level back up the tree and
            # try again
            if getattr(self_ancestor, 'parent', None):
                self_ancestor = self_ancestor.parent
            else:
                break

        if obj_parent != self_ancestor:
            raise RuntimeError(
                "Cannot add '{0}' to '{1}' because it is not a descendant "
                "of it or of any of its ancestors.".
                format(str(content), str(self)))

        if bubble_up:
            # If content has been passed on (is being bubbled up) then change
            # its parent to be this object
            content.root.parent = self.root

        import fparser
        if position[0] != "auto":
            # position[0] is not 'auto' so the baseclass can deal with it
            BaseGen.add(self, content, position)
        else:
            # position[0] == "auto" so insert in a context sensitive way
            if isinstance(content, DeclGen) or \
               isinstance(content, TypeDeclGen):

                if isinstance(content, DeclGen):
                    # have I already been declared?
                    for child in self._children:
                        if isinstance(child, DeclGen):
                            # is this declaration the same type as me?
                            if child.root.name == content.root.name:
                                # we are modifying the list so we need
                                # to iterate over a copy
                                for var_name in content.root.entity_decls[:]:
                                    for child_name in child.root.entity_decls:
                                        if var_name.lower() == \
                                           child_name.lower():
                                            content.root.entity_decls.\
                                                remove(var_name)
                                            if not content.root.entity_decls:
                                                # return as all variables in
                                                # this declaration already
                                                # exist
                                                return
                if isinstance(content, TypeDeclGen):
                    # have I already been declared?
                    for child in self._children:
                        if isinstance(child, TypeDeclGen):
                            # is this declaration the same type as me?
                            if child.root.selector[1] == \
                               content.root.selector[1]:
                                # we are modifying the list so we need
                                # to iterate over a copy
                                for var_name in content.root.entity_decls[:]:
                                    for child_name in child.root.entity_decls:
                                        if var_name.lower() == \
                                           child_name.lower():
                                            content.root.entity_decls.\
                                                remove(var_name)
                                            if not content.root.entity_decls:
                                                # return as all variables in
                                                # this declaration already
                                                # exist
                                                return

                index = 0
                # skip over any use statements
                index = self._skip_use_and_comments(index)
                # skip over implicit none if it exists
                index = self._skip_imp_none_and_comments(index)
                # skip over any declarations which have an intent
                try:
                    intent = True
                    while intent:
                        intent = False
                        for attr in self.root.content[index].attrspec:
                            if attr.find("intent") == 0:
                                intent = True
                                index += 1
                                break
                except AttributeError:
                    pass
            elif isinstance(content.root, fparser.statements.Use):
                # have I already been declared?
                for child in self._children:
                    if isinstance(child, UseGen):
                        if child.root.name == content.root.name:
                            # found an existing use with the same name
                            if not child.root.isonly and not \
                               content.root.isonly:
                                # both are generic use statements so
                                # skip this declaration
                                return
                            if child.root.isonly and not content.root.isonly:
                                # new use is generic and existing use
                                # is specific so we can safely add
                                pass
                            if not child.root.isonly and content.root.isonly:
                                # existing use is generic and new use
                                # is specific so we can skip this
                                # declaration
                                return
                            if child.root.isonly and content.root.isonly:
                                # we are modifying the list so we need
                                # to iterate over a copy
                                for new_name in content.root.items[:]:
                                    for existing_name in child.root.items:
                                        if existing_name.lower() == \
                                           new_name.lower():
                                            content.root.items.remove(new_name)
                                            if not content.root.items:
                                                return
                index = 0
            elif isinstance(content, ImplicitNoneGen):
                # does implicit none already exist?
                for child in self._children:
                    if isinstance(child, ImplicitNoneGen):
                        return
                # skip over any use statements
                index = 0
                index = self._skip_use_and_comments(index)
            else:
                index = len(self.root.content) - 1
            self.root.content.insert(index, content.root)
            self._children.append(content)

    def _skip_use_and_comments(self, index):
        ''' skip over any use statements and comments in the ast '''
        import fparser
        while isinstance(self.root.content[index],
                         fparser.statements.Use) or\
            isinstance(self.root.content[index],
                       fparser.statements.Comment):
            index += 1
        # now roll back to previous Use
        while isinstance(self.root.content[index-1],
                         fparser.statements.Comment):
            index -= 1
        return index

    def _skip_imp_none_and_comments(self, index):
        ''' skip over an implicit none statement if it exists and any
        comments before it '''
        import fparser
        end_index = index
        while isinstance(self.root.content[index],
                         fparser.typedecl_statements.Implicit) or\
            isinstance(self.root.content[index],
                       fparser.statements.Comment):
            if isinstance(self.root.content[index],
                          fparser.typedecl_statements.Implicit):
                end_index = index + 1
                break
            else:
                index = index + 1
        return end_index


class ModuleGen(ProgUnitGen):
    ''' create a fortran module '''
    def __init__(self, name="", contains=True, implicitnone=True):
        from fparser import api

        code = '''\
module vanilla
'''
        if contains:
            code += '''\
contains
'''
        code += '''\
end module vanilla
'''
        tree = api.parse(code, ignore_comments=False)
        module = tree.content[0]
        module.name = name
        endmod = module.content[len(module.content)-1]
        endmod.name = name
        ProgUnitGen.__init__(self, None, module)
        if implicitnone:
            self.add(ImplicitNoneGen(self))

    def add_raw_subroutine(self, content):
        ''' adds a subroutine to the module that is a raw f2py parse object.
            This is used for inlining kernel subroutines into a module.
        '''
        from parse import KernelProcedure
        if not isinstance(content, KernelProcedure):
            raise Exception(
                "Expecting a KernelProcedure type but received " +
                str(type(content)))
        content.ast.parent = self.root
        # add content after any existing subroutines
        index = len(self.root.content) - 1
        self.root.content.insert(index, content.ast)


class CommentGen(BaseGen):
    ''' Create a Fortran Comment '''
    def __init__(self, parent, content):
        reader = FortranStringReader("! content\n")
        reader.set_mode(True, True)  # free form, strict
        subline = reader.next()

        my_comment = Comment(parent.root, subline)
        my_comment.content = content

        BaseGen.__init__(self, parent, my_comment)


class DirectiveGen(BaseGen):
    ''' Base class for creating a Fortran directive. This is then sub-classed
    to support different types of directive, e.g. OpenMP or OpenACC. '''
    def __init__(self, parent, language, position, directive_type, content):

        self._supported_languages = ["omp"]
        self._language = language
        self._directive_type = directive_type

        reader = FortranStringReader("! content\n")
        reader.set_mode(True, True)  # free form, strict
        subline = reader.next()

        if language == "omp":
            my_comment = OMPDirective(parent.root, subline, position,
                                      directive_type)
            my_comment.content = "$omp"
            if position == "end":
                my_comment.content += " end"
            my_comment.content += " " + directive_type
            if content != "":
                my_comment.content += " " + content
        else:
            raise RuntimeError(
                "Error, unsupported directive language. Expecting one of "
                "{0} but found '{1}'".format(str(self._supported_languages),
                                             language))

        BaseGen.__init__(self, parent, my_comment)


class ImplicitNoneGen(BaseGen):
    ''' Generate a Fortran 'implicit none' statement '''
    def __init__(self, parent):

        if not isinstance(parent, ModuleGen) and not isinstance(parent,
                                                                SubroutineGen):
            raise Exception(
                "The parent of ImplicitNoneGen must be a module or a "
                "subroutine, but found {0}".format(type(parent)))
        reader = FortranStringReader("IMPLICIT NONE\n")
        reader.set_mode(True, True)  # free form, strict
        subline = reader.next()

        from fparser.typedecl_statements import Implicit
        my_imp_none = Implicit(parent.root, subline)

        BaseGen.__init__(self, parent, my_imp_none)


class SubroutineGen(ProgUnitGen):
    ''' Generate a Fortran subroutine '''
    def __init__(self, parent, name="", args=None, implicitnone=False):
        reader = FortranStringReader(
            "subroutine vanilla(vanilla_arg)\nend subroutine")
        reader.set_mode(True, True)  # free form, strict
        subline = reader.next()
        endsubline = reader.next()

        from fparser.block_statements import Subroutine, EndSubroutine
        self._sub = Subroutine(parent.root, subline)
        self._sub.name = name
        if args is None:
            args = []
        self._sub.args = args
        endsub = EndSubroutine(self._sub, endsubline)
        self._sub.content.append(endsub)
        ProgUnitGen.__init__(self, parent, self._sub)
        if implicitnone:
            self.add(ImplicitNoneGen(self))

    @property
    def args(self):
        ''' Returns the list of arguments of this subroutine '''
        return self._sub.args

    @args.setter
    def args(self, namelist):
        ''' sets the subroutine arguments to the values in the list provide.'''
        self._sub.args = namelist


class CallGen(BaseGen):
    ''' Generates a Fortran call of a subroutine '''
    def __init__(self, parent, name="", args=None):

        reader = FortranStringReader("call vanilla(vanilla_arg)")
        reader.set_mode(True, True)  # free form, strict
        myline = reader.next()

        from fparser.block_statements import Call
        self._call = Call(parent.root, myline)
        self._call.designator = name
        if args is None:
            args = []
        self._call.items = args

        BaseGen.__init__(self, parent, self._call)


class UseGen(BaseGen):
    ''' Generate a Fortran use statement '''
    def __init__(self, parent, name="", only=False, funcnames=None):
        reader = FortranStringReader("use kern,only : func1_kern=>func1")
        reader.set_mode(True, True)  # free form, strict
        myline = reader.next()
        root = parent.root
        from fparser.block_statements import Use
        use = Use(root, myline)
        use.name = name
        use.isonly = only
        if funcnames is None:
            funcnames = []
            use.isonly = False
        local_funcnames = funcnames[:]
        use.items = local_funcnames
        BaseGen.__init__(self, parent, use)


class AllocateGen(BaseGen):
    ''' Generates a Fortran allocate statement '''
    def __init__(self, parent, content):
        from fparser.statements import Allocate
        reader = FortranStringReader("allocate(dummy)")
        reader.set_mode(True, False)  # free form, strict
        myline = reader.next()
        self._decl = Allocate(parent.root, myline)
        if isinstance(content, str):
            self._decl.items = [content]
        elif isinstance(content, list):
            self._decl.items = content
        else:
            raise RuntimeError(
                "AllocateGen expected the content argument to be a str or"
                " a list, but found {0}".format(type(content)))
        BaseGen.__init__(self, parent, self._decl)


class DeallocateGen(BaseGen):
    ''' Generates a Fortran deallocate statement '''
    def __init__(self, parent, content):
        from fparser.statements import Deallocate
        reader = FortranStringReader("deallocate(dummy)")
        reader.set_mode(True, False)  # free form, strict
        myline = reader.next()
        self._decl = Deallocate(parent.root, myline)
        if isinstance(content, str):
            self._decl.items = [content]
        elif isinstance(content, list):
            self._decl.items = content
        else:
            raise RuntimeError(
                "DeallocateGen expected the content argument to be a str"
                " or a list, but found {0}".format(type(content)))
        BaseGen.__init__(self, parent, self._decl)


class DeclGen(BaseGen):
    ''' Generates a Fortran declaration for variables of intrinsic type '''
    def __init__(self, parent, datatype="", entity_decls=None, intent="",
                 pointer=False, kind="", dimension="", allocatable=False):
        if entity_decls is None:
            raise RuntimeError(
                "Cannot create a variable declaration without specifying the "
                "name(s) of the variable(s)")

        if datatype.lower() == "integer":
            from fparser.typedecl_statements import Integer
            reader = FortranStringReader("integer :: vanilla")
            reader.set_mode(True, False)  # free form, strict
            myline = reader.next()
            self._decl = Integer(parent.root, myline)
        elif datatype.lower() == "real":
            from fparser.typedecl_statements import Real
            reader = FortranStringReader("real :: vanilla")
            reader.set_mode(True, False)  # free form, strict
            myline = reader.next()
            self._decl = Real(parent.root, myline)
        else:
            raise RuntimeError(
                "f2pygen:DeclGen:init: Only integer and real are currently"
                " supported and you specified '{0}'".format(datatype))
        # make a copy of entity_decls as we may modify it
        local_entity_decls = entity_decls[:]
        self._decl.entity_decls = local_entity_decls
        my_attrspec = []
        if intent != "":
            my_attrspec.append("intent({0})".format(intent))
        if pointer is not False:
            my_attrspec.append("pointer")
        if allocatable is not False:
            my_attrspec.append("allocatable")
        self._decl.attrspec = my_attrspec
        if dimension != "":
            my_attrspec.append("dimension({0})".format(dimension))
        if kind is not "":
            self._decl.selector = ('', kind)
        BaseGen.__init__(self, parent, self._decl)


class TypeDeclGen(BaseGen):
    ''' Generates a Fortran declaration for variables of a derived type '''
    def __init__(self, parent, datatype="", entity_decls=None, intent="",
                 pointer=False, attrspec=None):
        if entity_decls is None:
            raise RuntimeError(
                "Cannot create a declaration of a derived-type variable "
                "without specifying the name(s) of the variable(s)")
        # make a copy of entity_decls as we may modify it
        local_entity_decls = entity_decls[:]
        if attrspec is None:
            attrspec = []
        my_attrspec = [spec for spec in attrspec]
        if intent != "":
            my_attrspec.append("intent({0})".format(intent))
        if pointer is not False:
            my_attrspec.append("pointer")
        self._names = local_entity_decls

        reader = FortranStringReader("type(vanillatype) :: vanilla")
        reader.set_mode(True, False)  # free form, strict
        myline = reader.next()

        from fparser.typedecl_statements import Type
        self._typedecl = Type(parent.root, myline)
        self._typedecl.selector = ('', datatype)
        self._typedecl.attrspec = my_attrspec
        self._typedecl.entity_decls = local_entity_decls
        BaseGen.__init__(self, parent, self._typedecl)

    @property
    def names(self):
        ''' Returns the names of the variables being declared '''
        return self._names

    @property
    def root(self):
        ''' Returns the associated Type object '''
        return self._typedecl


class TypeSelect(Select):
    ''' Generate a Fortran SELECT TYPE statement '''
    # TODO can this whole class be deleted?
    def tostr(self):
        return 'SELECT TYPE ( %s )' % (self.expr)


class TypeCase(Case):
    ''' Generate a Fortran SELECT CASE statement '''
    # TODO can this whole class be deleted?
    def tofortran(self, isfix=None):
        tab = self.get_indent_tab(isfix=isfix)
        type_str = 'TYPE IS'
        if self.items:
            item_list = []
            for item in self.items:
                item_list.append((' : '.join(item)).strip())
            type_str += ' ( %s )' % (', '.join(item_list))
        else:
            type_str = 'CLASS DEFAULT'
        if self.name:
            type_str += ' ' + self.name
        return tab + type_str


class SelectionGen(BaseGen):
    ''' Generate a Fortran SELECT block '''
    # TODO can this whole class be deleted?

    def __init__(self, parent, expr="UNSET", typeselect=False):
        ''' construct a ... '''
        from fparser.block_statements import EndSelect
        self._typeselect = typeselect
        reader = FortranStringReader(
            "SELECT CASE (x)\nCASE (1)\nCASE DEFAULT\nEND SELECT")
        reader.set_mode(True, True)  # free form, strict
        select_line = reader.next()
        self._case_line = reader.next()
        self._case_default_line = reader.next()
        end_select_line = reader.next()
        if self._typeselect:
            select = TypeSelect(parent.root, select_line)
        else:
            select = Select(parent.root, select_line)
        endselect = EndSelect(select, end_select_line)
        select.expr = expr
        select.content.append(endselect)
        BaseGen.__init__(self, parent, select)

    def addcase(self, casenames, content=None):
        ''' Add a case to this select block '''
        if content is None:
            content = []
        if self._typeselect:
            case = TypeCase(self.root, self._case_line)
        else:
            case = Case(self.root, self._case_line)
        case.items = [casenames]
        self.root.content.insert(0, case)
        idx = 0
        for stmt in content:
            idx += 1
            self.root.content.insert(idx, stmt.root)

    def adddefault(self):
        ''' Add the default case to this select block '''
        if self._typeselect:
            case_default = TypeCase(self.root, self._case_default_line)
        else:
            case_default = Case(self.root, self._case_default_line)
        self.root.content.insert(len(self.root.content)-1, case_default)


class DoGen(BaseGen):
    ''' Create a Fortran Do loop '''
    def __init__(self, parent, variable_name, start, end, step=None):
        reader = FortranStringReader("do i=1,n\nend do")
        reader.set_mode(True, True)  # free form, strict
        doline = reader.next()
        enddoline = reader.next()
        from fparser.block_statements import Do, EndDo
        dogen = Do(parent.root, doline)
        dogen.loopcontrol = variable_name + "=" + start + "," + end
        if step is not None:
            dogen.loopcontrol = dogen.loopcontrol + "," + step
        enddo = EndDo(dogen, enddoline)
        dogen.content.append(enddo)

        BaseGen.__init__(self, parent, dogen)

    def add(self, content, position=None, bubble_up=False):
        if position is None:
            position = ["auto"]

        if position[0] == "auto" and bubble_up:
            # There's currently no case where a bubbled-up statement
            # will live within a do loop so bubble it up again.
            self.parent.add(content, bubble_up=True)
            return

        if position[0] == "auto" or position[0] == "append":
            if position[0] == "auto" and bubble_up_type(content):
                # use and declaration statements cannot appear in a do loop
                # so pass on to parent
                self.parent.add(content, bubble_up=True)
                return
            else:
                # append at the end of the loop. This is not a simple
                # append as the last element in the loop is the "end
                # do" so we insert at the penultimate location
                BaseGen.add(self, content,
                            position=["insert", len(self.root.content)-1])
        else:
            BaseGen.add(self, content, position=position)


class IfThenGen(BaseGen):
    ''' Generate a fortran if, then, end if statement. '''

    def __init__(self, parent, clause):

        reader = FortranStringReader("if (dummy) then\nend if")
        reader.set_mode(True, True)  # free form, strict
        ifthenline = reader.next()
        endifline = reader.next()

        from fparser.block_statements import IfThen, EndIfThen
        my_if = IfThen(parent.root, ifthenline)
        my_if.expr = clause
        my_endif = EndIfThen(my_if, endifline)
        my_if.content.append(my_endif)

        BaseGen.__init__(self, parent, my_if)

    def add(self, content, position=None):
        if position is None:
            position = ["auto"]
        if position[0] == "auto" or position[0] == "append":
            if position[0] == "auto" and bubble_up_type(content):
                # use and declaration statements cannot appear in an if
                # block so pass on (bubble-up) to parent
                self.parent.add(content, bubble_up=True)
            else:
                # append at the end of the loop. This is not a simple
                # append as the last element in the if is the "end if"
                # so we insert at the penultimate location
                BaseGen.add(self, content,
                            position=["insert", len(self.root.content)-1])
        else:
            BaseGen.add(self, content, position=position)


class AssignGen(BaseGen):
    ''' Generates a Fortran statement where a value is assigned to a
        variable quantity '''

    def __init__(self, parent, lhs="", rhs="", pointer=False):
        if pointer:
            reader = FortranStringReader("lhs=>rhs")
        else:
            reader = FortranStringReader("lhs=rhs")
        reader.set_mode(True, True)  # free form, strict
        myline = reader.next()
        if pointer:
            from fparser.statements import PointerAssignment
            self._assign = PointerAssignment(parent.root, myline)
        else:
            from fparser.statements import Assignment
            self._assign = Assignment(parent.root, myline)
        self._assign.expr = rhs
        self._assign.variable = lhs
        BaseGen.__init__(self, parent, self._assign)
