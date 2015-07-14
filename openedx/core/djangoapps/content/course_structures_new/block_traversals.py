"""
TODO
"""

def traverse_blocks_pre_order(start_block, getter=None, get_children=None, block_access_checker=None):
    """
    TODO
    """
    getter = getter or (lambda block: block)
    get_children = get_children or (lambda block: block.get_children())
    block_access_checker = block_access_checker or (lambda __: True)

    stack = [start_block]

    while stack:

        curr_block = stack.pop()
        if not block_access_checker(curr_block):
            continue

        yield curr_block
        if curr_block.has_children:
            children = get_children(curr_block)
            for block in reversed(children):
                stack.append(block)

def traverse_blocks_topological(
        start_block,
        getter=None, get_parents=None, get_children=None, block_access_checker=None):
    """
    TODO
    """
    get_parents = get_parents or (lambda block: block.get_parents())

    visited_block_keys = set()
    block_gen = traverse_blocks_pre_order(
        start_block,
        getter=getter,
        block_access_checker=block_access_checker,
        get_children=get_children
    )

    for block in block_gen:
        parents = get_parents(block)
        all_parents_visited = all(parent.usage_key in visited_block_keys for parent in parents)
        if all_parents_visited:
            visited_block_keys.add(block.usage_key)
            yield block
