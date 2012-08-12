# -*- coding: utf-8 -*-

"""
What Todo

Plugin for Sublime Text 2 to highlight, jump to and export your TODOs

Copyright (c) 2012 Frédéric Massart - FMCorz.net

Licensed under The MIT License
Redistributions of files must retain the above copyright notice.

http://github.com/FMCorz/WhatTodo
"""

import re
from os.path import split
import sublime, sublime_plugin

s = sublime.load_settings('WhatTodo.sublime-settings')

class WhatTodoJumpCommand(sublime_plugin.TextCommand):

	def run(self, edit, backwards = False):
		wt = WhatTodo(self.view)
		wt.find()
		if not wt.has():
			sublime.status_message('No TODO found in this document')
		else:
			wt = WhatTodo(self.view)
			wt.jump(backwards = backwards)

	def is_enabled(self):
		return True

	def description(self):
		return None

class WhatTodoShowCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		wt = WhatTodo(self.view)
		wt.highlight()

	def is_enabled(self):
		return not s.get('auto_display')

	def description(self):
		return None

class WhatTodoHideCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		wt = WhatTodo(self.view)
		wt.hide()

	def is_enabled(self):
		wt = WhatTodo(self.view)
		return (not s.get('auto_display') and wt.hasHighlighted())

	def description(self):
		return None

class WhatTodoExportCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		wt = WhatTodo(self.view)
		wt.export()

	def is_enabled(self):
		return True

	def description(self):
		return None

class WhatTodoEvent(sublime_plugin.EventListener):

	def on_load(self, view):
		if not s.get('auto_display'):
			return
		wt = WhatTodo(view)
		if wt.canInSyntax():
			wt.highlight()

	def on_modified(self, view):
		if not s.get('auto_display'):
			return
		wt = WhatTodo(view)
		if wt.canInSyntax():
			wt.highlight()

class WhatTodo(object):

	lastrun = {}

	def __init__(self, view):
		self.view = view
		self.lastrun.setdefault(view.buffer_id(), 0)

	def canInSyntax(self):
		"""Validates the syntax against the user's preferences"""
		syntax = self.view.settings().get('syntax')
		syntax = split(syntax)[0].replace('Packages/', '')
		allowed = s.get('limit_to_syntax')
		if '*' in allowed or syntax in allowed:
			return True
		return False

	def export(self):
		"""Export the TODOs to a new buffer"""
		# Force the find in this thread upon export
		self._find()
		todos = self.extract()
		v = sublime.active_window().new_file()
		v.set_name('TODO export')
		e = v.begin_edit()
		fn = self.view.file_name() or 'Unsaved document'
		v.insert(e, v.size(), '%s\n\n' % fn)
		for (linenb, todo) in todos:
			s = u"{0:>5}:\t{1}\n".format(linenb, todo)
			v.insert(e, v.size(), s)
		v.end_edit(e)

	def extract(self):
		"""Extract the sanitized TODO along with its line number"""
		todos = []
		regions = self.get()
		for region in regions:
			shell_vars = self.shell_variables(region.begin())
			cs = shell_vars.setdefault('TM_COMMENT_START', None).strip()
			line = self.view.substr(self.view.line(region))
			todo = re.sub(r'.*%s\s*TODO\s*' % cs, '', line)
			linenb = self.view.rowcol(region.begin())[0]
			todos.append((linenb, todo))
		return todos

	def has(self):
		"""Return the number of regions"""
		return len(self.get())

	def hasHighlighted(self):
		"""Return the number of regions"""
		return len(self.view.get_regions('what_todo_highlight'))

	def hide(self):
		"""Hides the TODOs"""
		self.view.erase_regions('what_todo_highlight')

	def highlight(self):
		"""Creates an highlight timeout"""
		self.find()
		callback = lambda: self._highlight()
		sublime.set_timeout(callback, 10)

	def _highlight(self):
		"""Highlight the regions"""
		regions = self.view.get_regions('what_todo')
		self.view.add_regions('what_todo_highlight', regions, s.get('scope_name'), sublime.DRAW_OUTLINED if s.get('draw_outlined') else None)

	def find(self):
		"""Creates a find timeout"""
		callback = lambda: self._find()
		sublime.set_timeout(callback, 10)

	def _find(self):
		"""Find the regions"""
		if self.view.size() > s.get('threshold'):
			return

		kept = []
		todos = self.view.find_all(r'\bTODO\b')
		for todo in todos:

			# Make sure we are in a comment
			if not self.view.score_selector(todo.begin(), 'comment'):
				continue

			# Make sure TODO begins the comment
			shell_vars = self.shell_variables(todo.begin())
			cs = shell_vars.setdefault('TM_COMMENT_START', None).strip()
			line = self.view.substr(self.view.line(todo))
			if cs == None or not re.search(r'%s\s*TODO' % cs, line):
				continue

			kept.append(todo)

		self.view.add_regions('what_todo', kept, '')

	def get(self):
		"""Return the list of regions"""
		return self.view.get_regions('what_todo')

	def jump(self, backwards = False):
		"""Jump to the next TODO"""
		if not self.has():
			return
		regions = self.get()

		# Get the cursor position
		if s.get('jump_with_cursor'):
			wherearewe = self.view.sel()[0].begin()
		# Get the point where we last jumped
		else:
			wherearewe = self.view.settings().get('what_todo_jump', self.view.sel()[0].begin())

		jumpto = None

		if backwards:
			regions.reverse()

		for region in regions:
			if not backwards and wherearewe >= region.begin():
				continue
			elif backwards and wherearewe <= region.begin():
				continue
			else:
				jumpto = region
				break

		if jumpto == None:
			jumpto = regions[0]

		self.view.settings().set('what_todo_jump', jumpto.begin())

		if s.get('jump_with_cursor'):
			self.view.sel().clear()
			self.view.sel().add(jumpto.begin())

		self.view.show_at_center(jumpto)

	def shell_variables(self, pt):
		"""Return the meta info shellVariables"""
		shell_vars = self.view.meta_info("shellVariables", pt)
		if not shell_vars:
			return ([], [])
		all_vars = {}
		for v in shell_vars:
			if 'name' in v and 'value' in v:
				all_vars[v['name']] = v['value']
		return all_vars
