from sublime import Region, load_settings
import sublime_plugin
import re

from itertools import tee, chain

try:
    from itertools import izip as zip
except ImportError:  # will be 3.x series
    pass


def previous_and_current(iterable, *iterables):
    """
    Includes the previous value of iterable in iteration

    > previous_and_current([1,2,3])
    => (None, 1)
    => (1, 2)
    => (2, 3)
    """
    prevs, items = tee(iterable, 2)
    # Offset for the first element, since has no previous value
    prevs = chain([None], prevs)
    return zip(prevs, items, *iterables)


def is_comment_multi_line(view, region):
    return len(view.lines(region)) > 1


def normalize_comment(view, region):
    if is_comment_multi_line(view, region):
        return normalize_multiline_comment(view, region)
    else:
        return normalize_singleline_comment(view, region)


def normalize_singleline_comment(view, region):
    """
    Since single line comments include the newline
    if we don't explicitly make sure newline is kept
    out of the fold indicator, it will munge together
    with code. Example:

    // This is an example comment
    function foo() {

    Becomes:

    (..) function foo() {

    When what we really want is to keep the fold
    on it's own line, like so:

    (..)
    function foo() {
    """
    region_str = view.substr(region)
    last_newline = region_str.rfind('\n')

    if (last_newline == -1):
        # Single-line block comments don't include
        # their newline.
        # /* foo bar baz */ <-- like this
        return region
    else:
        return Region(region.begin(), region.begin() + last_newline)


def normalize_multiline_comment(view, region):
    """
    This is needed since in some languages it seems
    the boundaries for proper block-comments
    and chained single-line comments differ. The
    chaines single-line comments have the last point
    ( .end() .b etc) of their region set to the subsequent line,
    while the block comments have it set to the last char
    of their last line.

    Example where the @ char signifies
    the last endpoint:

    BLOCK COMMENT

    /**
     * This is an example comment
     */@ <---
    function foobar() {

    MULTIPLE SINGLE COMMENTS

    //
    // This is an example comment
    //
    @function foobar() { <---

    What we do to fix this is not to use the boundaries
    for the regions, but instead use the last line
    for the region - which seems to have the correct end
    point set.
    """
    lines = view.lines(region)
    last_line = lines[-1]
    last_point = last_line.b
    return Region(region.a, last_point)


class CommentNodes:

    def __init__(self, view):
        self.settings = load_settings("foldcomments.sublime-settings")
        self.view = view

    def find_comments(self):
        comments = self.find_comments_raw()
        comments = self.apply_settings(comments)
        comments = self.apply_filters(comments)
        return comments

    def find_comments_raw(self):
        comments = [
            normalize_comment(self.view, c) for c in
            self.view.find_by_selector('comment')
        ]
        if self.settings.get('fold_strings'):
            comments += [
                normalize_comment(self.view, c) for c in
                self.view.find_by_selector('string')
            ]
        return comments

    def apply_settings(self, comments):
        """Settings to apply before any processing"""
        if self.settings.get('concatenate_adjacent_comments'):
            comments = self.concatenate_adjacent_comments(comments)

        return comments

    def apply_filters(self, comments):
        """Filters to apply after processing"""
        if not self.settings.get('fold_single_line_comments'):
            comments = self.remove_single_line_comments(comments)

        if self.settings.get('ignore_assigned'):
            comments = self.remove_assigned(comments)

        if self.settings.get('show_first_line'):
            comments = self.show_first_line(comments)

        return comments

    def remove_single_line_comments(self, comments):
        return [
            c for c in comments if is_comment_multi_line(self.view, c)
        ]

    def concatenate_adjacent_comments(self, comments):
        """Merge any comments that are adjacent."""
        def concatenate(region1, region2):
            return region1.cover(region2)

        def is_adjacent(region1, region2):
            region_inbetween = Region(region1.end(), region2.begin())
            return len(self.view.substr(region_inbetween).strip()) == 0

        concatenated_comments = []

        for prev_comment, comment in previous_and_current(comments):
            concatenated_comment = None

            # prev wont be set on first iteration
            if prev_comment and is_adjacent(prev_comment, comment):
                concatenated_comment = concatenate(
                    concatenated_comments.pop(), comment
                )

            concatenated_comments.append(concatenated_comment or comment)

        return concatenated_comments

    def remove_assigned(self, comments):
        regex = re.compile(r"[\s\w]*\=")
        return [
            c for c in comments if not regex.match(self.view.substr(
                self.view.lines(c)[0]))
        ]

    def show_first_line(self, comments):
        """Leave the first line visible for multi line comments.

        Show the first line of the comment seeing as we are going
        to take up a line with (...) anyways.
        """
        # Regex of possible comment start characters.
        regex = re.compile(r"\s*@?(doc)?[\s\'\"\\\ \(\)\{\}#/*%<>!-=]*")
        new_fold = []
        for c in comments:
            if is_comment_multi_line(self.view, c):
                lines = self.view.lines(c)
                string = self.view.substr(lines[0])
                # Check if there is anything in the first line.
                if len(regex.match(string).group(0)) != len(string):
                    new_fold.append(Region(lines[0].end(), lines[-1].end()))
                else:
                    # Nothing in first line show the second line.
                    # Fold white space and comment characters at the
                    # start of the next line.
                    string = self.view.substr(lines[1])
                    new_fold.append(Region(
                        lines[0].end(),
                        lines[1].begin() + len(regex.match(string).group(0)))
                    )
                    new_fold.append(Region(lines[1].end(), lines[-1].end()))
            else:
                # Only change multiline comments.
                new_fold.append(c)

        return new_fold

    def fold_all(self):
        self.view.fold(self.find_comments())

    def unfold_all(self):
        self.view.unfold(self.find_comments())

    def is_folded(self, comments):
        return self.view.unfold(comments[0])  # False if /already folded/

    def toggle_fold_all(self):
        comments = self.find_comments()
        self.unfold_all() if self.is_folded(comments) else self.fold_all()

    def toggle_fold_current(self):
        comments = self.current_comments()
        if self.is_folded(comments):
            self.unfold_current()
        else:
            self.fold_current()

    def current_comments(self):
        comments = self.apply_settings(self.find_comments_raw())
        selected_comments = []
        for sel in (s for s in self.view.sel() if s.empty()):
            for comment in (c for c in comments if c.contains(sel)):
                selected_comments.append(comment)
        return self.apply_filters(selected_comments)

    def fold_current(self):
        self.view.fold(self.current_comments())

    def unfold_current(self):
        self.view.unfold(self.current_comments())


# ================================= COMMANDS ==================================

class ToggleFoldCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.toggle_fold_all()


class FoldCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.fold_all()


class UnfoldCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.unfold_all()


class ToggleFoldCurrentCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.toggle_fold_current()


class FoldCurrentCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.fold_current()


class UnfoldCurrentCommentsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        comments = CommentNodes(self.view)
        comments.unfold_current()


class FoldFileComments(sublime_plugin.EventListener):

    def on_load(self, view):
        if load_settings("foldcomments.sublime-settings").get('autofold'):
            comments = CommentNodes(view)
            comments.fold_all()
