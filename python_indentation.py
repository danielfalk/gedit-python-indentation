# -*- coding: utf-8 -*-
# Copyright (C) 2008 - Olivier Lauzanne
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Gedit Plugin : smart indentation for python code

The code is indented when the previous line ends with ':' and un-indented if
the previous line starts with 'return', 'pass', 'continue' or 'break'. This
plugin will use your tab configuration for indentation. To respect PEP8 you
should set tab width to 4 and choose to insert spaces instead of tabs.
"""

from gi.repository import GObject, Gtk, Gdk, Gedit

class PythonIndentation(GObject.Object, Gedit.ViewActivatable):
    """The python indentation plugin
    """
    __gtype_name__ = "PythonIndentation"

    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)
    

    def do_activate(self):
        self._doc = self.view.get_buffer()
        self.handlers = [
            (self.view, self.view.connect('notify::editable', self.on_notify_editable)),
            (self._doc, self._doc.connect('notify::language', self.on_notify_editable)),
        ]
        self.editHandlers = []
        self.update_active()
    
    def do_deactivate(self):
        for obj, handler in self.handlers + self.editHandlers:
            if handler:
                obj.disconnect(handler)
    
    def on_notify_editable(self, view, pspec):
        self.update_active()

    def update_active(self):
        lang = self._doc.get_language()
        if lang and lang.get_name() == 'Python' and self.view.get_editable():
            self.editHandlers.append(
                (self.view,
                self.view.connect('key-press-event', self.on_key_press)))
        else:
            for obj, handler in self.editHandlers:
                obj.disconnect(handler)
            self.editHandlers = []
    
    def on_key_press(self, view, event):
        """Check if the key press is 'Return' or 'Backspace' and indent or
        un-indent accordingly.
        """
        key_name = Gdk.keyval_name(event.keyval)
        if key_name not in ('Return', 'BackSpace') or \
           len(self._doc.get_selection_bounds()) != 0:
            # If some text is selected we want the default behavior of Return
            # and Backspace so we do nothing
            return

        if view.get_insert_spaces_instead_of_tabs():
            self.indent = ' ' * view.props.tab_width
        else:
            self.indent = '\t'

        if key_name == 'Return':
            line = self._get_current_line(self._doc)

            if line.endswith(':'):
                old_indent = line[:len(line) - len(line.lstrip())]
                indent = '\n' + old_indent + self.indent
                
                # Use insert_interactive instead of insert, so that the 
                # undo manager knows what we are doing (or something like that).
                # The True parameter is here because we are inserting into an
                # editable view
                self._doc.insert_interactive_at_cursor(indent, len(indent), True)
                self._scroll_to_cursor(self._doc, view)
                return True

            else:
                stripped_line = line.strip()
                n = len(line) - len(line.lstrip())
                if (stripped_line.startswith('return')
                    or stripped_line.startswith('break')
                    or stripped_line.startswith('continue')
                    or stripped_line.startswith('pass')
                    or stripped_line.startswith('raise')):
                    n -= len(self.indent)

                insert = '\n' + line[:n]
                self._doc.insert_interactive_at_cursor(insert, len(insert), True)
                self._scroll_to_cursor(self._doc, view)
                return True

        if key_name == 'BackSpace':
            line = self._get_current_line(self._doc)

            if line.strip() == '' and line != '':
                length = len(self.indent)
                nb_to_delete = len(line) % length or length
                self._delete_before_cursor(self._doc, nb_to_delete)
                self._scroll_to_cursor(self._doc, view)
                return True

    def _delete_before_cursor(self, buffer, nb_to_delete):
        cursor_position = buffer.get_property('cursor-position')
        iter_cursor = buffer.get_iter_at_offset(cursor_position)
        iter_before = buffer.get_iter_at_offset(cursor_position - nb_to_delete)
        buffer.delete_interactive(iter_before, iter_cursor, True)

    def _get_current_line(self, buffer):
        iter_cursor = self._get_iter_cursor(buffer)
        iter_line = buffer.get_iter_at_line(iter_cursor.get_line())
        return buffer.get_text(iter_line, iter_cursor, False)

    def _get_current_line_nb(self, buffer):
        iter_cursor = self._get_iter_cursor(buffer)
        return iter_cursor.get_line()

    def _get_iter_cursor(self, buffer):
        cursor_position = buffer.get_property('cursor-position')
        return buffer.get_iter_at_offset(cursor_position)

    def _scroll_to_cursor(self, buffer, view):
        lineno = self._get_current_line_nb(buffer) + 1
        insert = buffer.get_insert()
        view.scroll_mark_onscreen(insert)

