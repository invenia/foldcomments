from sublime import Region, load_settings
import sublime_plugin
import re

from itertools import tee, chain

try:
    from itertools import izip as zip
except ImportError:  # will be 3.x series
    pass


SYNTAX_RE = re.compile(r'([^/]+)\.(?:tmLanguage|sublime-syntax)$')


def get_syntax(view):
    """Return the view's syntax."""
    view_syntax = view.settings().get('syntax', '')

    match = SYNTAX_RE.search(view_syntax)

    if match:
        view_syntax = match.group(1)

    return view_syntax


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


class CommentNodes:

    def __init__(self, view):
        self.settings = load_settings("foldcomments.sublime-settings")
        self.view = view

    def find_comments(self):
        comments = self.find_comments_raw()
        comments = self.apply_pre_settings(comments)
        comments = self.apply_filters(comments)
        comments = self.apply_post_settings(comments)
        return comments

    def find_comments_raw(self):
        comments = [
            self.normalize(c) for c in
            self.view.find_by_selector('comment')
        ]
        if self.settings.get('fold_strings'):
            comments += [
                self.normalize(c) for c in
                self.view.find_by_selector('string') if
                self.is_multiline(c)  # Ignore single line strings.
            ]
        return comments

    def is_multiline(self, region):
        return len(self.view.lines(region)) > 1

    def nothing_before(self, region):
        return (
            len(self.view.substr(self.view.lines(region)[0]).split()) ==
            len(self.view.substr(
                self.view.split_by_newlines(region)[0]
            ).split())
        )

    def normalize(self, region):
        if self.is_multiline(region):
            return self.normalize_multiline(region)
        else:
            return self.normalize_singleline(region)

    def normalize_singleline(self, region):
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
        region_str = self.view.substr(region)
        last_newline = region_str.rfind('\n')

        if (last_newline == -1):
            # Single-line block comments don't include
            # their newline.
            # /* foo bar baz */ <-- like this
            return region
        else:
            return Region(region.begin(), region.begin() + last_newline)

    def normalize_multiline(self, region):
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
        lines = self.view.split_by_newlines(region)
        last_line = lines[-1]
        last_point = last_line.b
        return Region(region.a, last_point)

    def apply_pre_settings(self, comments):
        """Settings to apply before any processing."""
        if self.settings.get('concatenate_adjacent_comments'):
            comments = self.concatenate_adjacent_comments(comments)

        return comments

    def apply_filters(self, comments):
        """Filters to apply when folding all."""
        if not self.settings.get('fold_single_line_comments'):
            comments = self.remove_single_line_comments(comments)

        if self.settings.get('ignore_assigned'):
            comments = self.remove_assigned(comments)

        return comments

    def apply_post_settings(self, comments):
        """Settings to apply after processing."""
        if self.settings.get('show_first_line'):
            comments = self.show_first_line(comments)

        return comments

    def remove_single_line_comments(self, comments):
        return [
            c for c in comments if self.is_multiline(c)
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

            # prev wont be set on first iteration.
            # Only concatenate single line comments.
            if prev_comment and \
                    not self.is_multiline(prev_comment) and \
                    not self.is_multiline(comment) and \
                    self.nothing_before(prev_comment) and \
                    is_adjacent(prev_comment, comment):
                concatenated_comment = concatenate(
                    concatenated_comments.pop(), comment
                )

            concatenated_comments.append(concatenated_comment or comment)

        return concatenated_comments

    def remove_assigned(self, comments):
        regex = re.compile(r"^\s*\w[\s\w]*\=")
        return [
            c for c in comments if not regex.search(self.view.substr(
                self.view.lines(c)[0]))
        ]

    def show_first_line(self, comments):
        """Leave the first line visible for multi line comments.

        Show the first line of the comment seeing as we are going
        to take up a line with (...) anyways.
        """
        # Regex of possible comment start characters.
        string_regex = re.compile(r"^\s*\S*?([\'\"]+)\s*")
        # https://en.wikipedia.org/wiki/Comparison_of_programming_languages_(syntax)#Comment_comparison
        comment_regex = re.compile(
            r"""
            ^\s*
            (
                \"|\"{3}|\'|\'{3}|
                //|\/\*|\*|\*\/|
                \#|<\#|/\#|\#=|\|\#|\#\||
                \(\*?|\{\*?|%\{|
                %|%\{|--
            )
            \s*
            """,
            re.VERBOSE
        )

        new_fold = []
        for c in comments:
            if self.is_multiline(c):
                lines = self.view.split_by_newlines(c)
                string = self.view.substr(lines[0])

                match = string_regex.search(string)
                if not match:
                    match = comment_regex.search(string)

                # Unable to match string or comment.
                if not match:
                    continue

                # Check if there is anything in the first line.
                if len(match.group(0)) != len(string):
                    begin = lines[0].end()
                else:
                    # Nothing in first line show the second line.
                    # Fold white space and comment characters at the
                    # start of the next line.
                    string = self.view.substr(lines[1])
                    next_match = comment_regex.search(string)
                    if next_match:
                        absorb = len(next_match.group(0))
                    else:
                        absorb = len(re.search(r"\s*", string).group(0))

                    new_fold.append(Region(
                        lines[0].end(),
                        lines[1].begin() + absorb
                    ))
                    if len(lines) == 2:
                        # If it is a 2 line comment then we are done.
                        continue
                    begin = lines[1].end()

                end = lines[-1].end()
                if self.settings.get('show_closing_comment_characters'):
                    # Check if the last line ends with the
                    # comment start characters reversed.
                    #
                    # /*
                    #  * Example: /* is the reverse of */
                    #  */
                    string = self.view.substr(lines[-1])
                    comment_end = match.group(1).strip()[::-1]
                    if string.endswith(comment_end):
                        end = end - len(comment_end)

                new_fold.append(Region(begin, end))
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
        comments = self.apply_pre_settings(self.find_comments_raw())
        selected_comments = []
        for sel in (s for s in self.view.sel() if s.empty()):
            for comment in (c for c in comments if c.contains(sel)):
                selected_comments.append(comment)
        return self.apply_post_settings(selected_comments)

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
        settings = load_settings("foldcomments.sublime-settings")
        if settings.get('autofold'):
            syntaxes = settings.get('syntaxes')
            view_syntax = get_syntax(view)
            # If syntaxes is empty or view_syntax is in syntaxes
            # then we want to autofold.
            if not syntaxes or view_syntax in syntaxes:
                comments = CommentNodes(view)
                comments.fold_all()
            else:
                print(
                    "foldcomments: Did not autofold: \"{}\" not in syntaxes."
                    .format(view_syntax)
                )
