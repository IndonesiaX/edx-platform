"""
TODO
"""

from .block_traversals import traverse_blocks_topological


class MultiParentVisibilityRule(object):
    ACCESS_TO_ALL_REQUIRED = 0
    ACCESS_TO_ANY_REQUIRED = 1


class CourseStructureTransformation(object):

    def __init__(self, transformation_id):
        """
        Arguments:
            transformation_id (str)
        """
        self.id = transformation_id

    @property
    def required_fields(self):
        """
        Returns:
            set[Field]
        """
        return set()

    def collect(self, course, get_children, get_parents):
        """
        Arguments:
            course (CourseDescriptor)
            get_children (XBlock -> list[XBlock])
            get_parents (XBlock -> list[XBlock])

        Returns:
            dict[UsageKey: data_class]
        """
        pass

    def apply(self, root_block_key, block_cache_entries, user):
        """
        Arguments:
            root_block_key (UsageKey)
            block_cache_entries (dict[UsageKey: XBlockCacheEntry])
            user (User)
        """
        pass


class VisibilityTransformation(CourseStructureTransformation):

    transformation_attributes = ['multi_parent_visibility_rule']

    def __init__(self, transformation_id, multi_parent_visibility_rule):
        """
        Arguments:
            transformation_id (str)
            multi_parent_visibility_rule (MultiParentVisibilityRule)
        """
        super(VisibilityTransformation, self).__init__(transformation_id)
        self.multi_parent_visibility_rule = multi_parent_visibility_rule

    def collect(self, course, get_children, get_parents):
        """
        Arguments:
            course (CourseDescriptor)
            get_children (XBlock -> list[XBlock])
            get_parents (XBlock -> list[XBlock])

        Returns:
            dict[UsageKey: data_class]
        """
        block_gen = traverse_blocks_topological(
            start_block=course, get_parents=get_parents, get_children=get_children,
        )
        compose_staff_only_rule =(
            any if self.multi_parent_visibility_rule == MultiParentVisibilityRule.ACCESS_TO_ALL_REQUIRED
            else all
        )
        result_dict = {}
        for block in block_gen:
            # We know that all of the the block's parents have already been
            # visited because we're iterating over the result of a topological
            # sort.
            inherits_visible_to_staff_only = compose_staff_only_rule(
                result_dict[parent.usage_key] for parent in get_parents(block)
            )
            result_dict[block.usage_key] = {
                'visible_to_staff_only':
                    block.visible_to_staff_only or inherits_visible_to_staff_only
            }
        return result_dict

    def apply(self, root_block_key, block_cache_entries, user_info):
        """
        Arguments:
            root_block_key (UsageKey)
            block_cache_entries (dict[UsageKey: XBlockCacheEntry])
            user_info (CourseUserInfo)
        """
        for usage_key in block_cache_entries.keys():
            cache_entry = block_cache_entries[usage_key]
            block_accessible = (
                not cache_entry.get_transformation_data(self, 'visible_to_staff_only')
                or user_info.is_course_staff
            )
            if not block_accessible:
                for parent_key in cache_entry.parent_keys:
                    parent_info = block_cache_entries.get(parent_key, None)
                    if parent_info:
                        parent_info.child_keys.remove(usage_key)
                del block_cache_entries[usage_key]


ALL_TRANSFORMATIONS = [
    VisibilityTransformation('builtin.visibility', MultiParentVisibilityRule.ACCESS_TO_ALL_REQUIRED)
]
