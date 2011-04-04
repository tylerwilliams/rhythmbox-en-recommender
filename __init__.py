import rhythmdb, rb
import gobject, gtk
import gconf

import ConfigureDialog
import pyechonest.config
import pyechonest.playlist

pyechonest.config.ECHO_NEST_API_KEY="ACLRVJRBW78JSBI7V"

ui_toolbar_button = """
<ui>
  <toolbar name="ToolBar">
    <placeholder name="PluginPlaceholder">
      <toolitem name="ToolBarMakeGeniusPlaylist" action="MakeGeniusPlaylist"/>
    </placeholder>
  </toolbar>
</ui>

"""

class Recommender(rb.Plugin):
    def __init__(self):
        rb.Plugin.__init__(self)

    def activate(self, shell):
        self.shell = shell
        self.db = shell.props.db
        self.library = self.shell.props.library_source
        self.player = shell.props.shell_player
        data = dict()
        ui_manager = shell.get_ui_manager()
        
        icon_file_name = self.find_file("echo_logo_64a.png") 
        iconsource = gtk.IconSource() 
        iconsource.set_filename(icon_file_name) 
        iconset = gtk.IconSet() 
        iconset.add_source(iconsource) 
        iconfactory = gtk.IconFactory() 
        iconfactory.add("genius_icon", iconset) 
        iconfactory.add_default() 
        
        data['action_group'] = gtk.ActionGroup('GeniusPluginActions') 
        
        action = gtk.Action('MakeGeniusPlaylist', _('Echo Nest Recommender Playlist'), 
                            _("Make an Echo Nest Recommender playlist"), 
                            "genius_icon") 
        action.connect('activate', self.make_playlist, shell) 
        data['action_group'].add_action(action) 
        
        ui_manager.insert_action_group(data['action_group'], 0) 
        data['ui_id'] = ui_manager.add_ui_from_string(ui_toolbar_button) 
        ui_manager.ensure_update() 
        
        shell.set_data('GeniusPluginInfo', data)

    def deactivate(self, shell):
        print "deactivate!"
        data = shell.get_data('GeniusPluginInfo')
        ui_manager = shell.get_ui_manager()
        ui_manager.remove_ui(data['ui_id'])
        ui_manager.remove_action_group(data['action_group'])
        ui_manager.ensure_update()
        shell.set_data('GeniusPluginInfo', None) 
        self.player = None
        self.library = None
        self.source = None
        self.shell = None
        self.db = None
        self.dialog = None
        self.running = False

        del self.shell

    def create_configure_dialog(self):
        glade_file = self.find_file("en-recommender-prefs.glade")
        dialog = ConfigureDialog(glade_file, gconf_keys, self).get_dialog()
        dialog.present()
        return dialog

    def scan_library(self):
        """
        scan library and create an echonest personal catalog
        """
        def print_song(entry):
            uri = entry.get_playback_uri()
            artist = self.db.entry_get(entry, rhythmdb.PROP_ARTIST)
            title = self.db.entry_get(entry, rhythmdb.PROP_TITLE)
            print "%s - %s (%s)" % (artist,title,uri)
        
        library_query_model = self.library.props.base_query_model
        scan_iter = library_query_model.get_iter_first()
        while scan_iter is not None:
            entry = library_query_model.get(scan_iter, 0)[0]
            print_song(entry)
            scan_iter = library_query_model.iter_next(scan_iter)
    
    def get_selected_songs(self):
        """
        get all songs selected in the current window of the UI
        return a list of dicts w/ "artist", "title", and "uri" keys
        """
        def parse_entry_to_song_dict(entry):
            song_dict = {}
            song_dict['uri'] = entry.get_playback_uri()
            song_dict['artist'] = self.db.entry_get(entry, rhythmdb.PROP_ARTIST)
            song_dict['title'] = self.db.entry_get(entry, rhythmdb.PROP_TITLE)
            return song_dict

        entry_view = rb.Source.get_entry_view(self.shell.props.selected_page)
        entries = entry_view.get_selected_entries()
        return map(parse_entry_to_song_dict, entries)

    def create_source(self, playlist_name, playlist):
        entry_type = SampleEntryType()
        self.db.register_entry_type(entry_type)
        mysource = gobject.new(SampleSource, shell=self.shell, name=_(playlist_name), entry_type=entry_type)
        width, height = gtk.icon_size_lookup(gtk.ICON_SIZE_LARGE_TOOLBAR)
        icon = gtk.gdk.pixbuf_new_from_file_at_size(self.find_file("echo_logo_64a.png"), width, height)
        mysource.set_property("pixbuf", icon)
        group = rb.rb_display_page_group_get_by_id("playlists")
        self.shell.append_display_page (mysource, group)
        self.shell.register_entry_type_for_source(mysource, entry_type)
        for songobj in playlist:
            # don't put two same URIs in db...
            new_entry = self.db.entry_lookup_by_location(uri=songobj['uri']) or self.db.entry_new(entry_type, songobj['uri'] )
            self.db.set(new_entry, rhythmdb.PROP_ARTIST, songobj['artist'])
            self.db.set(new_entry, rhythmdb.PROP_TITLE, songobj['title'])
        self.db.commit()
        
    def set_playlist(self, data, **kwargs):
        """
        create a new "playlist" source in the ui and add the songs in data to it
        data is an en playlist
        """
        def parse_en_playlist(playlist):
            songs = []
            for songobj in playlist:
                song_dict = {}
                if not songobj.get_tracks('7digital'):
                    continue
                song_dict['artist'] = songobj.artist_name
                song_dict['title'] = songobj.title
                song_dict['uri'] = songobj.get_tracks('7digital')[0]['preview_url']
                songs.append(song_dict)
            return songs
        playlist = parse_en_playlist(data)
        
        if len(playlist) > 0:
            seed_artists = kwargs['seed_artists'][:3]
            playlist_name = ", ".join(seed_artists) 
            if len(playlist_name) > 25:
                playlist_name = playlist_name[:25] + "... Recommendations"
            else:
                playlist_name += " Recommendations"
            self.create_source(playlist_name, playlist)
        
    def popup_response_cb(self, dialog, response_id):
        dialog.destroy()

    def make_playlist(self, action, shell):
        """
        make a new playlist
        """
        print 'make playlist!'
        seed_songs = self.get_selected_songs()
        if len(seed_songs) < 1:
            message = _("Please select at least one song to base\n"\
                            + "recommendations on! (The Echo Nest API is\n"\
                            + "powerful, but not that powerful...)")
            dia = gtk.Dialog("Echo Nest Recommender", None, \
                                 gtk.DIALOG_DESTROY_WITH_PARENT,\
                                 (gtk.STOCK_OK, gtk.RESPONSE_OK))
            dia.vbox.set_spacing(10)
            hbox = gtk.HBox(False, 10)
            hbox.pack_start(gtk.image_new_from_stock(gtk.STOCK_DIALOG_INFO,gtk.ICON_SIZE_DIALOG))
            hbox.pack_start(gtk.Label(message))
            dia.vbox.pack_start(hbox)

            dia.connect('response', self.popup_response_cb)
            dia.show_all()
        else:
            # TODO: warn the user if they select more artists than we can use?
            artists = list(set([song['artist'] for song in seed_songs]))[:5]
            pyechonest.playlist.static(self.set_playlist, artist=artists, type='artist-radio', \
                                           buckets=['id:7digital','tracks'], limit=True, cb_kwargs={'seed_artists':artists})

class SampleEntryType(rhythmdb.EntryType):
    def __init__(self):
        rhythmdb.EntryType.__init__(self, name='7digital sample')

class SampleSource(rb.BrowserSource):
    def __init__(self):
        rb.BrowserSource.__init__(self)

gobject.type_register(SampleSource)
