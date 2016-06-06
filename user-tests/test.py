# pylint: disable-all
# flake8: noqa

# Settings for matching expected results:
# {
#    "concatenate_adjacent_comments": true,
#    "fold_single_line_comments": false,
#    "show_first_line": true,
#    "autofold": true | false,
#    "fold_strings": true,
#    "ignore_assigned": false
# }

# For each test the section before the "pass" keyword is what is too be
# folded. What comes after "pass" is a representation of how the folded
# text is expected to look like.


def comment_test1():
    # Comments that are not inline and occur right next to
    # each other should be combined into one.

    # Standalone lines should not be combined

    pass
    # Comments that are not inline and occur right next to ...

    # Standalone lines should not be combined


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
    # Comment adjacent to docstring

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
        "only triple quoted strings "
        "should be folded"
    )
    pass
    var = (
        "only triple quoted strings "
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
        shouldn't be auto folded
        """
    pass
    var = """ ... triple quoted string used in an assignment ... """
