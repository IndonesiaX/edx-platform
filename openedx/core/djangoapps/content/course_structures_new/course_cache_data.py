
class XBlockCacheEntry(object):

    def __init__(self, parent_keys, child_keys, block_fields, transformation_data):
        """
        Arguments:
            parent_keys (list[UsageKey])
            child_keys (list[UsageKey])
            block_fields (dict[str: *])
            transformation_data (dict[str: dict]):
                Dictionary mapping transformations' IDs to their collected data.
                {
                    'builtin.visibility': { 'visible_to_staff_only': ... }
                    'another_trans_id': { 'key1': value, 'key2': value2 ... }
                    ...
                }
        """
        self.parent_keys = parent_keys
        self.child_keys = child_keys
        self.block_fields = block_fields
        self._transformation_data = transformation_data

    def get_transformation_data(self, transformation_id, key):
        """
        Arguments:
            transformation: Transformation
            key: str

        Returns:
            *
        """
        if transformation_id in self._transformation_data:
            return self._transformation_data[transformation_id][key]
        else:
            raise KeyError(
                "Data for transformation with ID {} not found.".format(
                    transformation_id
                )
            )


class XBlockInformation(object):

    def __init__(self, child_keys, block_fields):
        """
        Arguments:
            child_keys (list[UsageKey])
            block_fields (dict[str: *])
        """
        self.child_keys = child_keys
        self.block_fields = block_fields

    @staticmethod
    def from_cache_entry(block_cache_entry):
        """
        Arguments:
            block_cache_entry (XBlockCacheEntry)

        Returns:
            XBlockInformation
        """
        return XBlockInformation(
            block_cache_entry.child_keys,
            block_cache_entry.block_fields
        )


class CourseUserInfo(object):
    """
    Information for a user in relation to a specific course.
    """

    def __init__(self):
        self.is_course_staff = None  # TODO: properly name (has_staff_access?)

    @staticmethod
    def load_from_course(user, course_key):
        """
        Arguments:
            course (CourseKey)

        Returns:
            CourseUserInfo
        """
        return CourseUserInfo()  # TODO: write this
