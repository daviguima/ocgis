import itertools
from abc import ABCMeta
from contextlib import contextmanager
from copy import copy, deepcopy

from ocgis import constants
from ocgis.util.helpers import get_iter


class AbstractOcgisObject(object):
    __metaclass__ = ABCMeta


class AbstractInterfaceObject(AbstractOcgisObject):
    __metaclass__ = ABCMeta

    def copy(self):
        """Return a shallow copy of self."""
        return copy(self)

    def deepcopy(self):
        """Return a deep copy of self."""
        return deepcopy(self)


class AbstractNamedObject(AbstractInterfaceObject):
    __metaclass__ = ABCMeta

    def __init__(self, name, aliases=None, source_name=constants.UNINITIALIZED, uid=None):
        self._aliases = None
        self._name = None
        self._source_name = source_name
        self.uid = uid

        self.set_name(name, aliases=aliases)

    @property
    def name(self):
        return self._name

    @property
    def source_name(self):
        if self._source_name == constants.UNINITIALIZED:
            ret = self._name
        else:
            ret = self._source_name
        return ret

    def append_alias(self, alias):
        self._aliases.append(alias)

    def is_matched_by_alias(self, alias):
        return alias in self._aliases

    def set_name(self, value, aliases=None):
        if aliases is None:
            aliases = []

        if self._source_name == constants.UNINITIALIZED:
            if self._name is None:
                self._source_name = value
            else:
                self._source_name = self._name

        self._name = value

        aliases.append(self._name)
        self._aliases = aliases


def is_empty_decorator(*args, **kwargs):
    print 'a', args, kwargs

    def wrapped_f(*args, **kwargs):
        print args, kwargs

    return wrapped_f


def get_dimension_names(target):
    from ocgis.variable.dimension import Dimension
    itr = get_iter(target, dtype=(basestring, Dimension))
    ret_names = []
    for element in itr:
        try:
            to_append = element.name
        except AttributeError:
            to_append = element
        ret_names.append(to_append)
    return tuple(ret_names)


def get_keyword_arguments_from_template_keys(kwargs, keys, ignore_self=True, pop=False):
    ret = {}
    for key in keys:
        if ignore_self and key == 'self':
            continue
        try:
            if pop:
                ret[key] = kwargs.pop(key)
            else:
                ret[key] = kwargs[key]
        except KeyError:
            # Pass on key errors to allow classes to overload default keyword argument values.
            pass
    return ret


def get_dimension_index(member, container):
    member = get_dimension_names(member)[0]
    container = get_dimension_names(container)
    return container.index(member)


def get_variable_names(target):
    from ocgis.variable.base import Variable
    itr = get_iter(target, dtype=(basestring, Variable))
    ret_names = []
    for element in itr:
        try:
            to_append = element.name
        except AttributeError:
            to_append = element
        ret_names.append(to_append)
    return tuple(ret_names)


def get_variables(target, parent):
    names = get_variable_names(target)
    ret = [None] * len(names)
    for idx, n in enumerate(names):
        ret[idx] = parent[n]
    return tuple(ret)


def iter_dict_slices(names, sizes, extra=None):
    extra = extra or []
    yld_extra = {e: slice(None) for e in extra}
    for indices in itertools.product(*[range(s) for s in sizes]):
        yld = {n: i for n, i in zip(names, indices)}
        if extra is not None:
            yld.update(yld_extra)
        yield yld


def iter_variables(target, container):
    names = get_variable_names(target)
    for name in names:
        yield container[name]


@contextmanager
def orphaned(target, keep_dimensions=False):
    if keep_dimensions:
        target._dimensions_cache = target.dimensions
    has_initialized_parent = target.has_initialized_parent
    if has_initialized_parent:
        original_parent = target.parent
        target.parent = None
    try:
        yield target
    finally:
        if has_initialized_parent:
            target.parent = original_parent
        if keep_dimensions:
            target._dimensions_cache = constants.UNINITIALIZED


@contextmanager
def renamed_dimensions(dimensions, name_mapping):
    original_names = [d.name for d in dimensions]
    try:
        items = name_mapping.items()
        for d in dimensions:
            for k, v in items:
                if d.name in v:
                    d._name = k
                    break
        yield dimensions
    finally:
        for d, o in zip(dimensions, original_names):
            d._name = o


@contextmanager
def renamed_dimensions_on_variables(vc, name_mapping):
    original_vc_dimensions = vc._dimensions
    original_names = {}
    new_vc_dimensions = copy(vc._dimensions)
    original_variable_dimension_names = {v.name: v.dimension_names for v in vc.values()}
    new_variable_dimension_names = copy(original_variable_dimension_names)
    mapping_meta = {}
    try:
        for k, v in name_mapping.items():
            for ki, vi in original_vc_dimensions.items():
                if ki in v:
                    new_vc_dimensions[k] = vi
                    original_name = new_vc_dimensions[k]._name
                    original_names[original_name] = k
                    new_vc_dimensions[k]._name = k
                    if original_name != k:
                        new_vc_dimensions.pop(original_name)
        for vname, vdimension_names in new_variable_dimension_names.items():
            to_set_dimensions = list(new_variable_dimension_names[vname])
            for vdn in vdimension_names:
                for ki, vi in name_mapping.items():
                    if vdn in vi:
                        to_set_dimensions[to_set_dimensions.index(vdn)] = ki
            new_variable_dimension_names[vname] = tuple(to_set_dimensions)
        for var in vc.values():
            var._dimensions = new_variable_dimension_names[var.name]
        vc._dimensions = new_vc_dimensions
        mapping_meta['variable_dimensions'] = original_variable_dimension_names
        mapping_meta['dimension_name_backref'] = original_names
        yield mapping_meta
    finally:
        for k, v in original_vc_dimensions.items():
            v._name = k
        vc._dimensions = original_vc_dimensions
        for var in vc.values():
            var._dimensions = original_variable_dimension_names[var.name]


def revert_renamed_dimensions_on_variables(mapping_meta, vc):
    for v in vc.values():
        v._dimensions = mapping_meta['variable_dimensions'][v.name]
    to_swap = []
    for k, v in vc.dimensions.items():
        for ki, vi in mapping_meta['dimension_name_backref'].items():
            if k == vi and ki != vi:
                vc.dimensions[k]._name = ki
                vc.dimensions[ki] = vc.dimensions[k]
                if k not in to_swap:
                    to_swap.append(k)
    for ts in to_swap:
        vc.dimensions.pop(ts)
