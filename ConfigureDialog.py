# ConfigureDialog.py

# Copyright (C) 2007,2008 Steven Brown

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gobject, gtk, gtk.glade
import gconf
from os import system, path

class ConfigureDialog (object):
	def __init__(self, glade_file, gconf_keys, plugin):
		self.gconf = gconf.client_get_default()
		self.gconf_keys = gconf_keys
		self.gladexml = gtk.glade.XML(glade_file)
		
		self.dialog = self.gladexml.get_widget("preferences_dialog")

		self.plugin = plugin

		self.toggle1 = self.gladexml.get_widget("option1")
		self.toggle2 = self.gladexml.get_widget("option2")

		self.dialog.connect("response", self.dialog_response)
		self.toggle1.connect('toggled', self.tb_toggled, 'toolbar_button')
		self.toggle2.connect('toggled', self.tb_toggled, 'context_menu')

		# set fields from gconf
		toolbar_button, context_menu = plugin.get_prefs()
		self.toggle1.set_active(toolbar_button == "1")
		self.toggle2.set_active(context_menu == "1")

	def dialog_response (self, dialog, response):
		dialog.hide()


	def tb_toggled (self, togglebutton, key):
		if (togglebutton.get_active()):
			self.plugin.set_gconf_key(key, "1")
		else:
			self.plugin.set_gconf_key(key, "0")
			
		self.plugin.update_ui()


	def get_dialog (self):
		return self.dialog
	
