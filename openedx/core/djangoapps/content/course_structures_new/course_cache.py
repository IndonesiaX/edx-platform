
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


def _get_block_cache_entries(root_block):
    """
    Arguments:
        root_block (XBlock)

    Returns:
        dict[UsageKey: XBlockCacheEntry]: All blocks under root_block_key.
            Contains information from the "collect" phase.
    """

    # Load entire course hierarchy.
    block_map = {}
    parent_map = {}
    child_map = {}
    _load_block_tree(root_block, block_map, parent_map, child_map)

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
        collected_data[transformation.__name__] = transformation.collect(root_block, get_children, get_parents)

    # Build a dictionary mapping usage keys to block information.
    return {
        usage_key: XBlockCacheEntry(
            usage_key,
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


def _get_block_information_for_user(user, course_key, root_block, block_cache_entries):
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
        transformation.apply(root_block, block_cache_entries, user_info)
    return {
        usage_key: XBlockInformation.from_cache_entry(cache_entry)
        for usage_key, cache_entry in block_cache_entries.iteritems()
    }
