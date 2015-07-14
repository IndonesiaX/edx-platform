
from collections import namedtuple

from .block_generators import generate_blocks_topological


class CourseStructureTransformation(object):

    required_fields = set()
    collected_data_class = namedtuple('EmptyTransformationData', '')

    @classmethod
    def collect(cls, course, get_children, get_parents):
        """
        Arguments:
            course (CourseDescriptor)
            get_children (XBlock -> list[XBlock])
            get_parents (XBlock -> list[XBlock])

        Returns:
            dict[UsageKey: data_class]
        """
        pass

    @classmethod
    def apply(cls, root_block_key, block_cache_entries, user):
        """
        Arguments:
            root_block_key (UsageKey)
            block_cache_entries (dict[UsageKey: XBlockCacheEntry])
            user (User)
        """
        pass


class VisibilityTransformation(CourseStructureTransformation):

    required_fields = set()
    collected_data_class = namedtuple('VisibilityTransformationData', 'visible_to_staff_only')

    @classmethod
    def collect(cls, course, get_children, get_parents):
        """
        Arguments:
            course (CourseDescriptor)
            get_children (XBlock -> list[XBlock])
            get_parents (XBlock -> list[XBlock])

        Returns:
            dict[UsageKey: data_class]
        """
        block_gen = generate_blocks_topological(
            course, get_parents, get_children
        )
        result_dict = {}
        for block in block_gen:
            # We know that all of the the block's parents have already been
            # visited because we're iterating over the result of a topological
            # sort.
            result_dict[block.usage_key] = cls.collected_data_class(
                visible_to_staff_only=(
                    block.visible_to_staff_only or
                    any(result_dict[parent.usage_key] for parent in get_parents())  # TODO: any or all???
                )
            )
        return result_dict

    @classmethod
    def apply(cls, root_block_key, block_cache_entries, user_info):
        """
        Arguments:
            root_block_key (UsageKey)
            block_cache_entries (dict[UsageKey: XBlockCacheEntry])
            user_info (CourseUserInfo)
        """
        for usage_key in block_cache_entries.keys():
            cache_entry = block_cache_entries[usage_key]
            block_accessible = (
                not cache_entry.get_transformation_data(cls).visible_to_staff_only
                or user_info.is_course_staff
            )
            if not block_accessible:
                for parent_key in cache_entry.parent_keys:
                    parent_info = block_cache_entries.get(parent_key, None)
                    if parent_info:
                        parent_info.child_keys.remove(usage_key)
                del block_cache_entries[usage_key]


TRANSFORMATIONS = [
    VisibilityTransformation
]
