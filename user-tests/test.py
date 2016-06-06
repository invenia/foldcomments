# pylint: disable-all
# flake8: noqa

# Settings for matching expected results:
# {
#    "concatenate_adjacent_comments": true,
#    "concatenate_multiline_comments": false,
#    "concatenate_over_empty_lines": false,
#    "fold_single_line_comments": false,
#    "show_first_line": true,
#    "show_closing_comment_characters": true,
#    "fold_strings": true,
#    "ignore_assigned": false
# }

# For each test the section before the "pass" keyword is what is too be
# folded. What comes after "pass" is a representation of how the folded
# text is expected to look like.


def comment_test1():
    # Comments that are not inline and occur right next to
    # each other should be combined into one.

    # Standalone lines are combined if concatenate_over_empty_lines is true.

    pass
    # Comments that are not inline and occur right next to ...

    # Standalone lines are combined if concatenate_over_empty_lines is true.


def comment_test2():
    # Comments that are not inline and occur right next to
    # each other should be combined into one.
    #
    # Not a standalone line

    pass
    # Comments that are not inline and occur right next to ...


def comment_test3():
    """
    A docstring
    """
    # Comment adjacent to docstring

    pass
    """ ... A docstring ... """
    # Comment adjacent to docstring


def comment_test4():
    """A docstring"""
    # Because these are both singline comments the get combined together.

    pass
    """A docstring""" ...


def comment_test5():
    var = []  # inline comment

    # Comment referring loop below which shouldn't be combined
    for i in range(10):
        var.append(i)

    pass
    var = []  # inline comment

    # Comment referring loop below which shouldn't be combined
    for i in range(10):
        var.append(i)


def string_test1():
    var = (
        "only triple quoted multiline strings "
        "should be folded"
    )
    pass
    var = (
        "only triple quoted multiline strings "
        "should be folded"
    )


def string_test2():
    # """
    # Commented out docstring should be treated as
    # a multiline comment
    # """
    pass
    # """ ...


def string_test3():
    var = """
        triple quoted string used in an assignment
        shouldn't be auto folded when ignore_assigned
        is true.
        """
    pass
    var = """ ... triple quoted string used in an assignment ... """


def string_test4():
    regex = re.compile(
        r"""
        hello\s*
        world\n
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    pass
    regex = re.compile(
        r""" ... hello\s* ... """,
        re.VERBOSE | re.IGNORECASE,
    )
