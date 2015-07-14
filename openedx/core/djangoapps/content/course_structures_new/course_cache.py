
from opaque_keys.edx.keys import CourseKey, UsageKey

from xmodule.modulestore.django import modulestore

from .course_cache_data import XBlockCacheEntry, XBlockInformation, CourseUserInfo
from .transformations import TRANSFORMATIONS


def _load_block_tree(block, block_map, parent_map, child_map):
    """
    Arguments:
        block (XBlock)
        block_map (dict[UsageKey: XBlock])
        parent_map (dict[UsageKey: list[UsageKey])
        child_map (dict[UsageKey: list[UsageKey])
    """
    block_map[block.usage_key] = block
    child_map[block.usage_key] = []

    children = block.get_children()
    for child in children:
        child_map[block.usage_key].append(child.usage_key)
        if child.usage_key in parent_map:
            # Child has already been visited.
            # Just add block to the existing parent_map entry.
            parent_map[child.usage_key].append(block.usage_key)
        else:
            # Child hasn't yet been visited.
            # Add it to parent_map and recurse.
            parent_map[child.usage_key] = [block.usage_key]
            _load_block_tree(child, block_map, parent_map, child_map)


def _create_block_cache_entries(course):
    """
    Arguments:
        course (CourseDescriptor)

    Returns:
        dict[UsageKey: XBlockCacheEntry]: Mapping of cache keys to block data.
            Contains information from the "collect" phase for all blocks under
            root_block.
    """
    # Load entire course hierarchy.
    block_map = {}
    parent_map = {}
    child_map = {}
    _load_block_tree(course, block_map, parent_map, child_map)

    # Define functions for traversing course hierarchy.
    get_children = lambda block: [
        block_map[child_key] for child_key in child_map[block.usage_key]
    ]
    get_parents = lambda block: [
        block_map[parent_key] for parent_key in parent_map[block.usage_key]
    ]

    # For each transformation, extract required fields and collect specially
    # computed data.
    required_fields = set()
    collected_data = {}
    for transformation in TRANSFORMATIONS:
        required_fields |= transformation.required_fields
        collected_data[transformation.__name__] = transformation.collect(course, get_children, get_parents)

    # Build a dictionary mapping usage keys to block information.
    return {
        usage_key: XBlockCacheEntry(
            parent_map[usage_key],
            child_map[usage_key],
            {
                required_field.__name__: getattr(block, required_field, None)
                for required_field in required_fields
            },
            {
                transformation_name: transformation_data[usage_key]
                for transformation_name, transformation_data in collected_data.iteritems()
            }
        )
        for usage_key, block in block_map.iteritems()
    }


def _load_user_blocks(user, course_key, root_block_key, block_cache_entries):
    """
    Arguments:
        user (User)
        course_key (CourseKey): Course to which desired blocks belong.
        root_block_key (UsageKey): Usage key for root block in the subtree
            for which block information will be returned. Passing in the usage
            key of a course will return the entire user-specific course
            hierarchy.
        block_cache_entries (dict[UsageKey: XBlockCacheEntry]): All blocks
            under root_block_key. Contains information from the "collect" phase.
            THIS DICTIONARY WILL BE MUTATED.
        user (User)

    Returns:
        dict[UsageKey: XBlockInformation]: User-specific blocks under
            root_block_key. Contains information from after the
            "apply" phase.

    Note:
        block_cache_entries will be mutated in place.
    """
    user_info = CourseUserInfo.load_from_course(user, course_key)

    for transformation in TRANSFORMATIONS:
        transformation.apply(root_block_key, block_cache_entries, user_info)
    return {
        usage_key: XBlockInformation.from_cache_entry(cache_entry)
        for usage_key, cache_entry in block_cache_entries.iteritems()
    }


def get_cache():
    """
    Returns:
        django cache instance
    """
    return ()  # TODO


# TODO: Is these key scheme good?

_CACHE_PREFIX = 'course_cache.'
_COURSE_PREFIX = _CACHE_PREFIX + 'course.'
_BLOCK_PREFIX = _CACHE_PREFIX + 'block.'
_LEN_COURSE_PREFIX = len(_COURSE_PREFIX)
_LEN_BLOCK_PREFIX = len(_BLOCK_PREFIX)


def _course_key_to_cache_key(course_key):
    """
    Arguments:
        course_key (CourseKey)

    Returns:
        str
    """
    return _COURSE_PREFIX + str(course_key)


def _usage_key_to_cache_key(usage_key):
    """
    Arguments:
        usage_key (UsageKey)

    Returns:
        str
    """
    return _BLOCK_PREFIX + str(usage_key)


def _cache_key_to_course_key(cache_key):
    """
    Arguments:
        cache_key (str)

    Returns:
        CourseKey
    """
    return CourseKey.from_string(cache_key[_LEN_COURSE_PREFIX:])


def _cache_key_to_usage_key(cache_key):
    """
    Arguments:
        cache_key (str)

    Returns:
        UsageKey
    """
    return UsageKey.from_string(cache_key[_LEN_BLOCK_PREFIX:])


def get_blocks(user, course_key, root_block_key):
    """
    Arguments:
        user (User)
        course_key (CourseKey): Course to which desired blocks belong.
        root_block_key (UsageKey): Usage key for root block in the subtree
            for which block information will be returned. Passing in the usage
            key of a course will return the entire user-specific course
            hierarchy.

    Returns:
        dict[UsageKey: XBlockInformation]
    """
    cache = get_cache()
    course_cache_key = _course_key_to_cache_key(course_key)
    block_cache_keys = cache.get(course_cache_key)

    if block_cache_keys is not None:
        block_cache_entries = {
            _cache_key_to_usage_key(cache_key): cache_entry
            for cache_key, cache_entry
            in cache.get(block_cache_keys).iteritems()
        }

    else:
        course = modulestore().get_course(course_key, depth=None)  # depth=None => load entire course
        block_cache_entries = _create_block_cache_entries(course)
        cache.set(
            course_cache_key,
            [block_cache_key for block_cache_key, __ in block_cache_entries]
        )
        cache.set_many({
            _usage_key_to_cache_key(usage_key): cache_entry
            for usage_key, cache_entry
            in block_cache_entries
        })

    return _load_user_blocks(
        user,
        course_key,
        root_block_key,
        block_cache_entries
    )
