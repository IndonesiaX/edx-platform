
class XBlockCacheEntry(object):

    def __init__(self, usage_key, parent_keys, child_keys, block_fields, transformation_data):
        """
        Arguments:
            usage_key (UsageKey)
            parent_keys (list[UsageKey])
            child_keys (list[UsageKey])
            block_fields (dict[str: *])
            transformation_data (dict[str: C], where C = data_class of transformation type):
                Dictionary containing data collected by each transformation.
                {
                    'VisibilityTransformation': VisibilityTransformation.data_class(...)
                    'StartTransformation': StartTransformation.data_class(...)
                    ...
                }
        """
        self.usage_key = usage_key
        self.parent_keys = parent_keys
        self.child_keys = child_keys
        self.block_fields = block_fields
        self._transformation_data = transformation_data

    def get_transformation_data(self, transformation_class):
        """
        Arguments:
            transformation_class (type): A subclass (the actual class; not an
                instance of it) of CourseStructureTransformation.

        Returns:
            transformation_class.collected_data_class: An instance of the
                transformation's collected data class containing the
        """
        name = transformation_class.__name__
        if name in self._transformation_data:
            return self._transformation_data[name]
        else:
            raise ValueError("Invalid transformation: {}".format(name))


class XBlockInformation(object):

    def __init__(self, usage_key, child_keys, block_fields):
        """
        Arguments:
            usage_key (UsageKey)
            child_keys (list[UsageKey])
            block_fields (dict[str: *])
        """
        self.usage_key = usage_key
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
            block_cache_entry.usage_key,
            block_cache_entry.child_keys,
            block_cache_entry.block_fields
        )


class CourseUserInfo(object):
    """
    Information for a user in relation to a specific course.
    """

    def __init__(self):
        self.is_course_staff = None

    @staticmethod
    def load_from_course(user, course):
        """
        Arguments:
            course (CourseDescriptor)

        Returns:
            CourseUserInfo
        """
        pass  # todo
