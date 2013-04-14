
import sys
import imp
import ast
import weakref
import random
from ast import *
from core import *
from util import *


@singleton
class placeholder(object):
    def __repr__(self):
        return "placeholder"


def macro(func):
    Macros.registry[func.func_name] = func


expr.__repr__ = lambda self: ast.dump(self, annotate_fields=False)




def splat(node):
    """Extracts the `lineno` and `col_offset` from the given node as a dict.
    meant to be used e.g. through Str("omg", **splat(node)) to transfer the old
    `lineno` and `col_offset` to the newly created node.
    """
    return {"lineno": node.lineno, "col_offset": node.col_offset}


def interpolate_ast(node, values):
    def v(): return values

    def func(node):
        if node is placeholder:
            val = v().pop(0)
            return ast_repr(val)

        else:
            return Macros.recurse(node, func)
    return func(node)


@singleton
class Macros(object):
    registry = {}

    def recurse(self, node, func):
        if type(node) is list:
            return flatten([func(x) for x in node])
        elif isinstance(node, AST):
            for field, old_value in iter_fields(node):
                old_value = getattr(node, field, None)
                new_value = func(old_value)
                setattr(node, field, new_value)
            return node
        else:
            return node


class MacroLoader(object):
    def __init__(self, module_name, txt, file_name):
        self.module_name = module_name
        self.txt = txt
        self.file_name = file_name

    def load_module(self, module_name):
        """see http://www.python.org/dev/peps/pep-0302/ if you don't know what
        a lot of this stuff is for"""
        if module_name in sys.modules:
            return sys.modules[module_name]
        a = expand_ast(ast.parse(self.txt))

        code = compile(a, module_name, 'exec')

        mod = imp.new_module(module_name)
        mod.__file__ = self.file_name
        mod.__loader__ = self

        exec code in mod.__dict__

        sys.modules[module_name] = mod
        return mod


def expand_ast(node):
    def macro_search(node):

        if isinstance(node, With):
            for func in Macros.registry:
                if func.func_name == node.context_expr.id:
                    expansion = func(node)
                    return Macros.recurse(expansion, macro_search)
        if isinstance(node, BinOp) \
                and type(node.left) is Name \
                and type(node.op) is Mod \
                and node.left.id in Macros.registry:
            #for g in globals().items():
            #    print "A", g

            expansion = Macros.registry[node.left.id](node.right)
            return Macros.recurse(expansion, macro_search)
        return Macros.recurse(node, macro_search)
    node = macro_search(node)
    return node

@singleton
class MacroFinder(object):
    def find_module(self, module_name, package_path):

        if module_name in sys.modules:
            return None
        try:
            (file, pathname, description) = imp.find_module(module_name.split('.')[-1], package_path)

            if file is not None:
                print "Found", module_name
                txt = file.read()
                if "from macros import *" in txt:
                    return MacroLoader(module_name, txt, file.name)
        except ImportError, e:
            return None


sys.meta_path.append(MacroFinder)


