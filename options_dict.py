from base import OptionsBaseException
from formatters import SimpleFormatter, TreeFormatter
from types import FunctionType
from string import Template
from copy import deepcopy
from warnings import warn



class OptionsDictException(OptionsBaseException):
    pass

class NodeInfoException(OptionsBaseException):
    pass

        
class OptionsDict(dict):
    """
    An OptionsDict inherits from a conventional dict, but it has a few
    enhancements:
    
    (1) In a similar way to Django and Jinja2, entries can be set and
        accessed using attribute setter/getter (dot) syntax.  
        For example, as an alternative to
            opt['foo'] = 'bar'
            print opt['foo']
        we may write
            opt.foo = 'bar'
            print opt.foo

        To prevent clashes with the existing attribute namespace,
        - Any name registered in the mutable_attributes class variable
          escapes item setting so that the associated attribute can be
          manipulated as usual.
        - Setting an item with a name registered in protected_attributes,
          or with a leading underscore, is disallowed.

        As an added convenience, the OptionsDict can be constructed or
        updated from a class whose attributes represent the new
        entries.  Any class methods will go on to become dependent
        entries (see next note).
            class basis:
                foo = 'bar'
                def baz(self):
                    return self.foo
            opt.update(basis)
        
    (2) Values can be runtime-dependent upon the state of other values
        in the dictionary.  Each of these special values is specified
        by a function accepting a single dictionary argument (i.e. the
        OptionsDict itself).  The argument is used to look things up
        dynamically.  An OptionsDict can be constructed or updated
        with a list of functions instead of the usual key-value pairs,
        in which case the functions' names become the keys.

        N.B.  If dependent entries are created using more exotic
        constructs such lambdas or closures, it will be necessary to
        call OptionsDict.remove_links before using the multiprocessing
        module, because it seems that such constructs cause pickling
        problems.  remove_links gets around the problems by converting the
        dependent entries back to independent ones.

    (3) An OptionsDict can be given 'node information' which lends the
        OptionsDict a name and describes its position in a tree.  This
        node information accumulates when OptionsDicts are merged via
        the update() method, and can be used to form a string
        identifier for the ensemble.  For example, updating node 'A'
        with node 'B' will produce node 'A_B'.  The identifier can be
        accessed via the usual str() idiom, but a get_string() method is
        also provided with optional arguments for customising the
        identifier and inferring the identifiers of other
        combinations.

    (4) An OptionsDict can expand strings as simple templates.  (For
        more complex templates, it is recommended that the OptionsDict
        be passed to a template engine such as Jinja2.)
    """

    # mutable attributes should be prefixed with underscores so that
    # the client does not confuse them with dictionary items.
    mutable_attributes = ['_node_info']
    protected_attributes = [
        'donate_copy', 'indent', 'create_node_info_formatter', 
        'expand_template_string', 'remove_links', 'get_position',
        'get_node_info', 'get_string', 'set_node_info', 
        'update']
    
    def __init__(self, entries={}):
        """
        Returns an OptionsDict with no node information.  The entries
        argument can be more than just key-value pairs; see the update
        method for more information.
        """
        # With just an entries argument, treat as a simple dict.  Set
        # the node_info list first.  This is necessary to prevent
        # dependent entries from possibly referencing the component
        # before it exists.
        self._node_info = []
        self.update(entries)

    
    def update(self, entries):
        """
        As with conventional dicts, updates entries with the key-value
        pairs given in the entries argument.  Alternatively, a list of
        functions may be supplied which will go on to become dependent
        entries, or a class may be supplied whose attributes and
        methods will go on to become conventional and dependent entries,
        respectively.
        """
        default_err = OptionsDictException(
            "\nArgument must be a dict, an iterable of dependent entries "+\
            "(i.e. functions),\nor a class with attributes and/or methods.")
        for strategy in [self._update_from_dict,
                         self._update_from_dependent_entries,
                         self._update_from_class]:
            try:
                strategy(entries, default_err)
                return
            except (AttributeError, TypeError):
                # tolerate certain exceptions by moving onto the next
                # update strategy
                pass

        # if we've looped through all the strategies and come to the end, 
        # the argument was incompatible
        raise default_err


    def remove_links(self, recursive=False):
        """
        Converts all dependent entries to independent ones.  This may be
        necessary before multiprocessing, because Python's native
        pickle module has trouble serialising any lambdas (anonymous
        functions) residing in the dict, or before passing to a
        template engine.
        """
        kwargs = {'recursive': recursive}
        for k in self.keys():
            self[k] = self[k]
            
            if recursive:
                self._try_remove_links(self[k], **kwargs)
                self._try_remove_links_iterable(self[k], **kwargs)
        
        # return self so as to be inlineable
        return self
    
            
    def get_string(self, only=[], exclude=[], absolute={}, relative={}, 
            formatter=None, only_indent=False):
        """
        Returns a string identifier, providing more control than the
        str() idiom through optional arguments.

        Specifically, if the OptionsDict was part of a collection
        and/or has been updated from other such OptionsDicts, it is
        possible to control which substrings appear through the 'only'
        and 'exclude' arguments.  These arguments take a collection
        name or list of collection names.

        If the OptionsDict was part of a tree, the 'absolute' and
        'relative' arguments can be used to infer the name of an
        OptionsDict corresponding to a different node in the tree.
        These arguments take the form of key-value pairs with
        collection names as the keys and indices as the values.  In
        accordance with Python indexing rules, a negative absolute
        index returns a node from the end of the array.  To prevent
        confusion, however, this shall not apply when a relative index
        is given.
        
        If the formatter argument is a string or omitted, the
        OptionsDict constructs and applies a formatter object (see
        OptionsDict.create_node_info_formatter).  Alternatively, the
        client may construct and pass a formatter object directly.
        """
        # wrap 'only' and 'exclude' strings as lists if necessary
        if isinstance(only, str):
            only = [only]
        if isinstance(exclude, str):
            exclude = [exclude]

        # filter the nodes to represent
        filtered_node_info = []
        for ni in self._node_info:
            # filter nodes according to corresponding collection names
            # given in the optional args
            if only:
                if not ni.belongs_to_any(only):
                    continue
            if ni.belongs_to_any(exclude):
                continue
            # if we are still in the loop at this point, we can include
            # the current node info in the result.
            filtered_node_info.append(ni)

        # create a formatter object if necessary
        if isinstance(formatter, str) or not formatter:
            formatter = self.create_node_info_formatter(formatter)
            
        # pass the filtered list to the formatter object
        return formatter(filtered_node_info, 
                         absolute=absolute, relative=relative,
                         only_indent=only_indent)
    
        
    def create_node_info_formatter(self, which=None):
        """
        Overrideable factory method, used by OptionsDict.get_string().  The
        argument may be 'simple', 'tree', or omitted (defaulting to
        'simple').
        """
        if not which:
            which = 'simple'
        if which == 'simple':
            formatter = SimpleFormatter()
        elif which == 'tree':
            formatter = TreeFormatter()
        else:
            raise OptionsDictException("'{}' not recognised.".format(which))
        return formatter

            
    def indent(self, only=[], exclude=[], absolute={}, relative={}, 
            formatter='tree'):
        return self.get_string(
            only=only, exclude=exclude, absolute=absolute, relative=relative,
            formatter=formatter, only_indent=True)
            
        
    def get_node_info(self, collection_name=None):
        """
        Returns the OptionDict's first NodeInfo object.  If the
        OptionsDict has accumulated several NodeInfo objects, the
        client can get a particular one by passing in the
        corresponding collection name.
        """
        if collection_name is None:
            try:
                return self._node_info[0]
            except IndexError:
                raise NodeInfoException(
                    "there aren't any node_info objects")
        else:
            for ni in self._node_info:
                if ni.belongs_to(collection_name):
                    return ni
            raise NodeInfoException(
                "couldn't find any node information corresponding to '{}'".\
                format(collection_name))

        
    def set_node_info(self, new_node_info, collection_name=None):
        """
        Sets the OptionDict's first NodeInfo object.  If the
        OptionsDict has accumulated several NodeInfo objects, the
        client can set a particular one by passing in the
        corresponding collection name.
        """
        if collection_name is None:
            try:
                self._node_info[0] = new_node_info
            except IndexError:
                self._node_info.append(new_node_info)
        else:
            for i, ni in enumerate(self._node_info):
                if ni.belongs_to(collection_name):
                    self._node_info[i] = new_node_info
                    return
            raise NodeInfoException(
                "couldn't find any node information corresponding to '{}'".\
                format(collection_name))


    def get_position(self, collection_name=None):
        """
        Returns the OptionDict's position in the present collection.  If
        the OptionsDict is part of a tree, the client can get the
        position with respect to a particular collection by passing in
        the collection name.
        """
        return self.get_node_info(collection_name).position
        
        
    def expand_template_string(self, buffer_string, loops=1):
        """
        In buffer_string, replaces substrings prefixed '$' with
        corresponding values in the OptionsDict.  More than one loop
        will be needed if the placeholders are nested.
        """
        for i in range(loops):
            buffer_string = Template(buffer_string).safe_substitute(self)
        # this next line will flag any unexpanded placeholders as
        # KeyErrors
        Template(buffer_string).substitute({})
        return buffer_string


    def donate_copy(self, acceptor):
        # polymorphic; used by tree elements
        acceptor.update(self)
        return acceptor, []

    
    def _update_from_dict(self, other, default_error):
        # update OptionsDict attributes
        if isinstance(other, OptionsDict):
            self._node_info += other._node_info
            # if len(self._node_info) > 1: raise Exception
        # now check item names and pass to superclass
        for k in other.keys():
            self._check_new_item_name(k)
        dict.update(self, other)

        
    def _update_from_dependent_entries(self, functions, default_error):
        for func in functions:
            if not isinstance(func, FunctionType):
                raise default_error
            varnames = func.func_code.co_varnames
            self._check_new_item_name(func.__name__)
            self[func.__name__] = func

            
    def _update_from_class(self, basis_class, default_error):
        # recurse through the basis_class' superclasses first
        if basis_class.__bases__:
            for b in basis_class.__bases__:
                self._update_from_class(b, default_error)

        # ignore magic/hidden attributes, which are prefixed with
        # a double underscore
        entries = {k: basis_class.__dict__[k] \
                   for k in basis_class.__dict__.keys() \
                   if '__' not in k}
        # can now call update again
        self.update(entries)

        
    def _check_new_item_name(self, name):
        if name[0] == '_':
            raise OptionsDictException(
                "\nPrefixing an item with an underscore is not allowed "+\
                "because it \nmight clash with a hidden attribute.  If you "+\
                "want to set this attribute,\n you will need to register "+\
                "the name in mutable_attributes.")
        elif name in self.protected_attributes:
            raise OptionsDictException(
                "\nSetting an item called '{}' is not allowed because it "+\
                "would clash \nwith an attribute of the same name.  If you "+\
                "want to set this attribute,\n you will need to register "+\
                "the name in mutable_attributes.")

    @staticmethod
    def _try_remove_links(item, **kwargs):
        try:
            item.remove_links(**kwargs)
        except AttributeError:
            pass

    @classmethod
    def _try_remove_links_iterable(cls, item, **kwargs):
        try:
            for el in item:
                cls._try_remove_links(el, **kwargs)
        except TypeError:
            pass
        
    def __str__(self):
        return self.get_string()

    def __repr__(self):
        return dict.__repr__(self) + repr(self._node_info)

    def __iter__(self):
        yield self

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError("'{}'".format(name))

    def __setattr__(self, name, value):
        if name in self.mutable_attributes:
            self.__dict__[name] = value
        else:
            self._check_new_item_name(name)
            self[name] = value
        
    def __eq__(self, other):
        result = isinstance(other, OptionsDict)
        if result:
            result *= self._node_info == other._node_info
            result *= dict.__eq__(self, other)
        return result

    def __ne__(self, other):
        return not self==other
    
    def __getitem__(self, key):
        try:
            value = dict.__getitem__(self, key)
        except:
            raise
        # recurse until the return value is no longer a function
        if isinstance(value, FunctionType):
            # dependent entry
            return value(self)
        else:
            # normal entry
            return value

        
class CallableEntry:
    """
    Because the OptionsDict works by evaluating all function objects
    recursively, it is not able to return other functions specified by
    the client unless these are wrapped as callable objects.  This class
    provides such a wrapper.
    """
    def __init__(self, function):
        self.function = function
        
    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


class Lookup:
    """
    Provides a function object that simply looks up a key in a
    dictionary.  This functionality was originally implemented as a
    closure, but the multiprocessing module couldn't pickle it.
    """
    def __init__(self, key):
        self.key = key

    def __call__(self, dictionary):
        return dictionary[self.key]


class GetString:
    """
    Provides a function object that calls the get_string() method when
    passed an OptionsDict.  Optional arguments can be given upon
    initialisation.  See OptionsDict.get_string for further
    information.
    """
    def __init__(self, only=[], exclude=[], absolute={}, relative={}, 
                 formatter=None):
        self.only = only
        self.exclude = exclude
        self.absolute = absolute
        self.relative = relative
        self.formatter = formatter

    def __call__(self, options_dict):
        return options_dict.get_string(
            only=self.only, exclude=self.exclude, absolute=self.absolute,
            relative=self.relative, formatter=self.formatter)

    
def remove_links(options_dicts, **kwargs):
    """
    Converts dependent entries to dependent ones.  See
    OptionsDict.remove_links for further information.
    """
    result = deepcopy(options_dicts)
    for od in result:
        od.remove_links(**kwargs)
    return result
