from __future__ import annotations
import json
import os
from pathlib import Path
import threading
import traceback
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango
from . import core, theme, VERSION
from .i18n import STRINGS

KIND_ICONS={'video':'video-x-generic','audio':'audio-x-generic','pdf':'application-pdf','spreadsheet':'x-office-spreadsheet',
 'presentation':'x-office-presentation','ebook':'x-office-document','document':'x-office-document'}
STATUS_MARKS={'pending':('•','muted'),'running':('◐','info'),'done':('✓','success'),'failed':('✕','danger'),'cancelled':('■','warning')}
THEME_ICONS={'system':'preferences-desktop-display-symbolic','light':'weather-clear-symbolic','dark':'weather-clear-night-symbolic'}

class Window(Gtk.ApplicationWindow):
    def __init__(self,app,paths):
        super().__init__(application=app)
        self.config=theme.settings_path()
        self.settings_data=theme.load_settings()
        self.lang=self.settings_data.get('language','tr')
        if self.lang not in STRINGS: self.lang='tr'
        self.output=Path(self.settings_data.get('output',str(Path.home()/'Dönüştürülenler')))
        self.theme_mode=theme.stored_mode(); self.active_theme=None; self.portal_scheme=None
        self.items={}; self.next_id=1; self.running=False; self.detecting=False; self.runner=None; self.stopping=False
        self.bindings=[]; self.current=None; self.pulse_source=None; self.progress_total=0; self.progress_done=0
        width,height=self.settings_data.get('window_size',[1100,800])
        self.set_default_size(max(int(width),860),max(int(height),680)); self.set_size_request(860,680)
        if self.settings_data.get('maximized'):self.maximize()
        self.set_icon_name('donusturucu')
        self.connect('delete-event',self.on_close)
        self.css=Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.watch_portal()
        self.build()
        self.install_actions(app)
        self.apply_theme()
        self.retranslate()
        self.options_box.set_no_show_all(True)
        self.show_all(); self.empty.show(); self.options_box.hide(); self.update_queue_view()
        GLib.timeout_add_seconds(2,self.watch_system_theme)
        if paths: GLib.idle_add(self.add_paths,paths)

    def t(self,key): return STRINGS[self.lang].get(key,key)
    def style(self,w,name): w.get_style_context().add_class(name); return w
    def label(self,key,css=None):
        w=Gtk.Label(xalign=0); self.bindings.append((w,key,'label'))
        if css: self.style(w,css)
        return w
    def button(self,key,callback,css=None,icon=None):
        b=Gtk.Button(); self.bindings.append((b,key,'button')); b.connect('clicked',callback)
        if icon:b.set_image(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.BUTTON));b.set_always_show_image(True)
        if css:self.style(b,css)
        return b
    def vbox(self,space=10): return Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=space)
    def combo(self,entries):
        combo=Gtk.ComboBoxText()
        for ident,label in entries: combo.append(ident,label)
        combo.set_active(0)
        return combo

    # ---- Theme -------------------------------------------------------------
    def watch_portal(self):
        # Cache the portal value; a live D-Bus signal keeps it current without polling the bus.
        self.portal_scheme=theme._portal_scheme()
        try:
            bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
            bus.signal_subscribe('org.freedesktop.portal.Desktop','org.freedesktop.portal.Settings','SettingChanged','/org/freedesktop/portal/desktop',None,Gio.DBusSignalFlags.NONE,self.on_portal_changed)
            self.portal_bus=bus
        except Exception:pass
    def on_portal_changed(self,conn,sender,path,iface,signal,params):
        namespace,key,value=params.unpack()
        if namespace=='org.freedesktop.appearance' and key=='color-scheme':
            try:self.portal_scheme=int(value)
            except (TypeError,ValueError):self.portal_scheme=None
            GLib.idle_add(self.apply_theme)
    def watch_system_theme(self):
        if self.theme_mode=='system' and theme.resolve('system',self.portal_scheme)!=self.active_theme:self.apply_theme()
        return True
    def apply_theme(self,*_):
        resolved=theme.resolve(self.theme_mode,self.portal_scheme)
        settings=Gtk.Settings.get_default()
        # A neutral base theme keeps buttons, dialogs and file pickers consistent with our palette.
        if settings.props.gtk_theme_name!='Adwaita':settings.props.gtk_theme_name='Adwaita'
        settings.props.gtk_application_prefer_dark_theme=resolved=='dark'
        if resolved!=self.active_theme:
            self.active_theme=resolved;self.palette=theme.PALETTES[resolved]
            self.css.load_from_data(theme.gtk_css(resolved))
            if hasattr(self,'tree'):self.tree.queue_draw()
            self.save_settings()
        if hasattr(self,'theme_image'):self.theme_image.set_from_icon_name(THEME_ICONS[self.theme_mode],Gtk.IconSize.BUTTON)
        return False
    def set_theme_mode(self,mode):
        if mode not in theme.MODES:return
        self.theme_mode=mode
        for key,button in self.theme_buttons.items():
            if button.get_active()!=(key==mode):button.set_active(key==mode)
        self.apply_theme();self.save_settings()
    def on_theme_toggled(self,button,mode):
        if button.get_active() and mode!=self.theme_mode:self.set_theme_mode(mode)
    def toggle_theme(self,*_):self.set_theme_mode('light' if self.active_theme=='dark' else 'dark')

    # ---- Layout ------------------------------------------------------------
    def build(self):
        head=Gtk.HeaderBar(show_close_button=True)
        head.props.title='Dönüştür'
        self.set_titlebar(head); self.header=head
        self.menu_button=Gtk.MenuButton(); self.menu_button.set_image(Gtk.Image.new_from_icon_name('open-menu-symbolic',Gtk.IconSize.BUTTON))
        self.style(self.menu_button,'flat'); head.pack_end(self.menu_button)
        self.theme_button=Gtk.MenuButton(); self.theme_image=Gtk.Image.new_from_icon_name(THEME_ICONS[self.theme_mode],Gtk.IconSize.BUTTON)
        self.theme_button.set_image(self.theme_image); self.style(self.theme_button,'flat'); head.pack_end(self.theme_button)
        self.theme_button.set_popover(self.build_theme_popover())
        self.language=self.combo([('tr','Türkçe'),('ku','Kurmancî')]); self.language.set_active_id(self.lang)
        self.language.connect('changed',self.change_language); head.pack_end(self.language)
        self.dep_button=Gtk.Button()  # Kept for callers; the action lives in the main menu.
        outer=self.vbox(14); outer.set_border_width(22); self.add(outer)
        hero=Gtk.Box(spacing=18)
        titles=self.vbox(2); titles.pack_start(self.label('title','hero-title'),False,False,0)
        titles.pack_start(self.label('tagline','subtitle'),False,False,0)
        hero.pack_start(titles,True,True,0)
        badge=self.label('offline','badge'); badge.set_valign(Gtk.Align.CENTER); hero.pack_end(badge,False,False,0)
        outer.pack_start(hero,False,False,0)
        self.drop_box=drop=self.style(Gtk.Box(spacing=20),'drop')
        icon=Gtk.Image.new_from_icon_name('document-send-symbolic',Gtk.IconSize.DIALOG); drop.pack_start(icon,False,False,4)
        text=self.vbox(4); text.set_valign(Gtk.Align.CENTER); text.pack_start(self.label('drop','section'),False,False,0); text.pack_start(self.label('drop_sub','hint'),False,False,0)
        drop.pack_start(text,True,True,0)
        self.add_button=self.button('add',self.choose_files,'suggested-action','list-add-symbolic'); self.add_button.set_valign(Gtk.Align.CENTER); drop.pack_end(self.add_button,False,False,0)
        self.folder_add_button=self.button('add_folder',self.choose_folder,icon='folder-new-symbolic'); self.folder_add_button.set_valign(Gtk.Align.CENTER); drop.pack_end(self.folder_add_button,False,False,0)
        outer.pack_start(drop,False,False,0)
        self.drag_dest_set(Gtk.DestDefaults.ALL,[],Gdk.DragAction.COPY); self.drag_dest_add_uri_targets()
        self.connect('drag-data-received',self.on_drop)
        self.connect('drag-motion',self.on_drag_motion); self.connect('drag-leave',self.on_drag_leave)
        body=Gtk.Box(spacing=14); outer.pack_start(body,True,True,0)
        left=self.style(self.vbox(10),'card'); body.pack_start(left,True,True,0)
        queue_head=Gtk.Box(spacing=8); queue_head.pack_start(self.label('queue','section'),False,False,0)
        self.queue_count=self.style(Gtk.Label(xalign=1),'hint'); queue_head.pack_end(self.queue_count,False,False,0)
        left.pack_start(queue_head,False,False,0)
        note=self.label('batch_note','hint'); note.set_line_wrap(True); left.pack_start(note,False,False,0)
        # Hidden id, displayed columns, unlocalized status key, kind icon.
        self.model=Gtk.ListStore(int,str,str,str,str,str,str)
        self.tree=Gtk.TreeView(model=self.model); self.tree.set_headers_visible(True)
        self.columns=[]
        for index,key in enumerate(('file','type','format','status'),1):
            cell=Gtk.CellRendererText(); cell.set_property('ellipsize',Pango.EllipsizeMode.MIDDLE); cell.set_property('ypad',5)
            col=Gtk.TreeViewColumn(''); col.set_resizable(True)
            if index==1:
                pix=Gtk.CellRendererPixbuf(); pix.set_property('xpad',4); col.pack_start(pix,False); col.add_attribute(pix,'icon-name',6)
            col.pack_start(cell,True)
            if index==2:cell.set_property('ellipsize',Pango.EllipsizeMode.END)
            if index==4:cell.set_property('ellipsize',Pango.EllipsizeMode.NONE)
            if index==4:col.set_cell_data_func(cell,self.render_status)
            else:col.add_attribute(cell,'text',index)
            col.set_min_width({1:180,2:165,3:70,4:135}[index])
            if index==1: col.set_expand(True)
            self.tree.append_column(col); self.columns.append((col,key))
        self.tree.get_selection().connect('changed',self.selection_changed)
        self.tree.connect('row-activated',self.on_row_activated); self.tree.connect('button-press-event',self.on_tree_button)
        scroll=Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(160); scroll.add(self.tree); self.style(scroll,'queue-frame')
        self.tree.set_tooltip_column(1)
        empty_box=self.vbox(8); empty_box.set_valign(Gtk.Align.CENTER); empty_box.set_halign(Gtk.Align.CENTER)
        empty_icon=self.style(Gtk.Image.new_from_icon_name('folder-documents-symbolic',Gtk.IconSize.DIALOG),'empty-icon'); empty_icon.set_pixel_size(56)
        empty_box.pack_start(empty_icon,False,False,0)
        empty_title=self.label('empty_queue','empty-title'); empty_title.set_xalign(.5); empty_box.pack_start(empty_title,False,False,0)
        empty_sub=self.label('empty_queue_sub','hint'); empty_sub.set_xalign(.5); empty_sub.set_justify(Gtk.Justification.CENTER); empty_sub.set_line_wrap(True); empty_box.pack_start(empty_sub,False,False,0)
        self.queue_stack=Gtk.Stack(); self.queue_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.queue_stack.add_named(empty_box,'empty'); self.queue_stack.add_named(scroll,'list'); left.pack_start(self.queue_stack,True,True,0)
        controls=Gtk.Box(spacing=8)
        self.remove_button=self.button('remove',self.remove_item,icon='list-remove-symbolic')
        self.clear_button=self.button('clear',self.clear_items,icon='edit-clear-all-symbolic')
        controls.pack_start(self.remove_button,False,False,0); controls.pack_start(self.clear_button,False,False,0)
        self.extras_button=self.button('extras',self.open_extras,icon='applications-utilities-symbolic')
        controls.pack_end(self.extras_button,False,False,0)
        left.pack_start(controls,False,False,0)
        right=self.style(self.vbox(12),'card'); right.set_size_request(300,-1)
        settings_scroll=Gtk.ScrolledWindow(); settings_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); settings_scroll.add(right)
        settings_scroll.set_size_request(330,-1); body.pack_end(settings_scroll,False,False,0)
        right.pack_start(self.label('settings','section'),False,False,0)
        self.empty=self.label('select','hint'); self.empty.set_line_wrap(True); right.pack_start(self.empty,False,False,0)
        self.options_box=self.vbox(9); right.pack_start(self.options_box,False,False,0)
        self.options_box.pack_start(self.label('target'),False,False,0)
        self.target_combo=Gtk.ComboBoxText(); self.options_box.pack_start(self.target_combo,False,False,0)
        self.target_combo.connect('changed',self.settings_changed)
        self.apply_all=Gtk.CheckButton();self.bindings.append((self.apply_all,'apply_all','button'));self.options_box.pack_start(self.apply_all,False,False,0)
        self.format_count=Gtk.Label(xalign=0);self.style(self.format_count,'hint');self.options_box.pack_start(self.format_count,False,False,0)
        self.media_box=self.vbox(8); self.options_box.pack_start(self.media_box,False,False,0)
        self.video_box=self.vbox(7); self.media_box.pack_start(self.video_box,False,False,0)
        self.quality_box=self.vbox(7); self.video_box.pack_start(self.quality_box,False,False,0)
        self.quality_box.pack_start(self.label('quality'),False,False,0)
        self.quality_combo=self.combo([('original',''),('small',''),('balanced',''),('high','')]); self.quality_combo.set_active_id('balanced')
        self.quality_combo.connect('changed',self.settings_changed); self.quality_box.pack_start(self.quality_combo,False,False,0)
        self.video_box.pack_start(self.label('resolution'),False,False,0)
        self.res_combo=self.combo([('original',''),('1080','1080p'),('720','720p'),('480','480p')]); self.res_combo.connect('changed',self.settings_changed)
        self.video_box.pack_start(self.res_combo,False,False,0)
        self.audio_box=self.vbox(7); self.media_box.pack_start(self.audio_box,False,False,0)
        self.text_box=self.vbox(7);self.options_box.pack_start(self.text_box,False,False,0)
        self.only_text=Gtk.CheckButton();self.bindings.append((self.only_text,'only_text','button'));self.text_box.pack_start(self.only_text,False,False,0)
        self.use_ocr=Gtk.CheckButton();self.bindings.append((self.use_ocr,'use_ocr','button'));self.text_box.pack_start(self.use_ocr,False,False,0)
        self.ocr_lang=self.combo([('tur+eng','Türkçe + English'),('kmr+eng','Kurmancî + English'),('eng','English'),('ara+eng','العربية / Arapça + English'),('fas+eng','فارسی / Farsça + English'),('ara+fas+eng','العربية + فارسی + English'),('tur+kmr+eng','Türkçe + Kurmancî + English')]);self.text_box.pack_start(self.label('ocr_language'),False,False,0);self.text_box.pack_start(self.ocr_lang,False,False,0)
        self.only_text.connect('toggled',self.settings_changed);self.use_ocr.connect('toggled',self.settings_changed);self.ocr_lang.connect('changed',self.settings_changed)
        self.note=Gtk.Label(xalign=0); self.note.set_line_wrap(True); self.note.set_max_width_chars(36); self.style(self.note,'hint')
        self.options_box.pack_start(self.note,False,False,2)
        folder=self.style(Gtk.Box(spacing=10),'card'); outer.pack_start(folder,False,False,0)
        folder_icon=Gtk.Image.new_from_icon_name('folder-open-symbolic',Gtk.IconSize.LARGE_TOOLBAR); folder.pack_start(folder_icon,False,False,0)
        folder_text=self.vbox(2); folder_text.pack_start(self.label('output','section'),False,False,0)
        self.folder_label=Gtk.Label(label=str(self.output),xalign=0); self.folder_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE); self.style(self.folder_label,'hint')
        folder_text.pack_start(self.folder_label,False,False,0); folder.pack_start(folder_text,True,True,0)
        self.open_folder_button=self.button('open',self.open_output); self.open_folder_button.set_valign(Gtk.Align.CENTER); folder.pack_end(self.open_folder_button,False,False,0)
        self.folder_button=self.button('choose',self.choose_output); self.folder_button.set_valign(Gtk.Align.CENTER); folder.pack_end(self.folder_button,False,False,0)
        self.progress=Gtk.ProgressBar(); outer.pack_start(self.progress,False,False,0)
        footer=Gtk.Box(spacing=10)
        self.status=Gtk.Label(xalign=0); self.status.set_line_wrap(True); self.style(self.status,'hint'); footer.pack_start(self.status,True,True,0)
        self.log_button=self.button('details',self.show_log); footer.pack_end(self.log_button,False,False,0)
        self.stop_button=self.button('cancel',self.cancel,'stop-action','process-stop-symbolic'); self.stop_button.set_sensitive(False); footer.pack_end(self.stop_button,False,False,0)
        self.start_button=self.button('start',self.start,'suggested-action','media-playback-start-symbolic'); self.start_button.set_sensitive(False); footer.pack_end(self.start_button,False,False,0)
        outer.pack_start(footer,False,False,0)
        self.logs=[]; self.loading_selection=False

    def build_theme_popover(self):
        pop=Gtk.Popover(); box=self.vbox(10); box.set_border_width(14); pop.add(box)
        box.pack_start(self.label('theme','menu-heading'),False,False,0)
        linked=Gtk.Box(); self.style(linked,'linked'); box.pack_start(linked,False,False,0)
        self.theme_buttons={}; group=None
        for mode in theme.MODES:
            b=Gtk.RadioButton.new_from_widget(group); group=group or b; b.set_mode(False)
            b.set_image(Gtk.Image.new_from_icon_name(THEME_ICONS[mode],Gtk.IconSize.BUTTON)); b.set_always_show_image(True)
            self.style(b,'mode-button'); self.bindings.append((b,'theme_'+mode,'button'))
            b.set_active(mode==self.theme_mode); b.connect('toggled',self.on_theme_toggled,mode)
            linked.pack_start(b,True,True,0); self.theme_buttons[mode]=b
        hint=self.label('theme_hint','hint'); hint.set_line_wrap(True); hint.set_max_width_chars(34); box.pack_start(hint,False,False,0)
        box.show_all(); return pop

    def build_main_menu(self):
        menu=Gio.Menu()
        files=Gio.Menu(); files.append(self.t('add'),'win.add-files'); files.append(self.t('add_folder'),'win.add-folder'); files.append(self.t('extras'),'win.extras')
        tools=Gio.Menu(); tools.append(self.t('details'),'win.log'); tools.append(self.t('dependencies'),'win.tools')
        info=Gio.Menu(); info.append(self.t('shortcuts'),'win.shortcuts'); info.append(self.t('about'),'win.about')
        for section in (files,tools,info):menu.append_section(None,section)
        self.menu_button.set_menu_model(menu)

    def install_actions(self,app):
        entries=[('add-files',self.choose_files,['<Primary>o']),('add-folder',self.choose_folder,['<Primary><Shift>o']),
            ('remove',self.remove_item,['Delete']),('start',self.start,['<Primary>Return','<Primary>KP_Enter']),('stop',self.cancel,['Escape']),
            ('log',self.show_log,['<Primary>l']),('extras',self.open_extras,['<Primary>e']),('tools',self.show_tools,[]),
            ('toggle-theme',self.toggle_theme,['<Primary><Shift>t']),('shortcuts',self.show_shortcuts,['<Primary>question','F1']),
            ('about',self.show_about,[]),('quit',lambda *_:self.close(),['<Primary>q']),
            ('open-result',self.open_selected_result,[]),('show-result',self.show_selected_result,[])]
        self.actions={}
        for name,callback,accels in entries:
            action=Gio.SimpleAction.new(name,None); action.connect('activate',lambda a,p,cb=callback:cb()); self.add_action(action); self.actions[name]=action
            if app and accels:app.set_accels_for_action('win.'+name,accels)
        self.update_actions()

    def update_actions(self):
        if not hasattr(self,'actions'):return
        idle=not self.running and not self.detecting; result=self.selected_result()
        for name in ('add-files','add-folder','remove','extras'):self.actions[name].set_enabled(idle)
        self.actions['start'].set_enabled(idle and bool(len(self.model)))
        self.actions['stop'].set_enabled(self.running and not self.stopping)
        self.actions['open-result'].set_enabled(bool(result)); self.actions['show-result'].set_enabled(bool(result))

    def save_settings(self):
        try:
            data=theme.load_settings()
            data.update(language=self.lang,output=str(self.output),theme=self.theme_mode,active_theme=self.active_theme)
            if self.get_realized():
                maximized=bool(self.get_window() and self.get_window().get_state()&Gdk.WindowState.MAXIMIZED)
                data['maximized']=maximized
                if not maximized:data['window_size']=list(self.get_size())
            self.config.parent.mkdir(parents=True,exist_ok=True)
            self.config.write_text(json.dumps(data,ensure_ascii=False))
        except OSError: pass

    def retranslate(self):
        title=self.t('title')
        self.set_title(title); self.header.props.title=title
        for w,key,_ in self.bindings: w.set_label(self.t(key))
        for col,key in self.columns:col.set_title(self.t(key))
        self.language.set_tooltip_text(self.t('language'))
        self.theme_button.set_tooltip_text(self.t('theme')+' (Ctrl+Shift+T)'); self.menu_button.set_tooltip_text(self.t('menu'))
        self.progress.set_tooltip_text(self.t('progress'))
        self.add_button.set_tooltip_text('Ctrl+O'); self.folder_add_button.set_tooltip_text('Ctrl+Shift+O'); self.start_button.set_tooltip_text('Ctrl+Enter'); self.stop_button.set_tooltip_text('Esc')
        self.build_main_menu()
        self.loading_selection=True
        for combo,keys in [(self.quality_combo,['original','small','balanced','high']),(self.res_combo,['original','1080','720','480'])]:
            active=combo.get_active_id(); combo.remove_all()
            for key in keys:combo.append(key,self.t('keep_source' if combo is self.quality_combo and key=='original' else key) if not key.isdigit() else key+'p')
            combo.set_active_id(active)
        self.loading_selection=False
        for row in self.model:
            item=self.items[row[0]]; row[2]=self.kind_label(item['info']); row[4]=self.t(row[5])
        self.status.set_text(self.t('busy' if self.running else 'idle'))
        self.update_queue_view(); self.refresh_selection()

    def change_language(self,combo):
        self.lang=combo.get_active_id(); self.retranslate(); self.save_settings()

    def kind_label(self,info):
        return self.t(info.kind)+' · '+info.fmt.upper()

    def render_status(self,column,cell,model,itr,data=None):
        key=model[itr][5]; mark,color=STATUS_MARKS.get(key,('•','muted'))
        palette=getattr(self,'palette',theme.PALETTES['light'])
        cell.set_property('markup',f'<span foreground="{palette[color]}" weight="bold">{mark}</span>  {GLib.markup_escape_text(model[itr][4])}')

    def update_queue_view(self):
        count=len(self.model)
        self.queue_stack.set_visible_child_name('list' if count else 'empty')
        self.queue_count.set_text(self.t('queue_count').format(count=count) if count else '')
        self.remove_button.set_sensitive(bool(count) and not self.running and not self.detecting)
        self.clear_button.set_sensitive(bool(count) and not self.running and not self.detecting)
        self.update_actions()

    def dialog(self,title,text,kind=Gtk.MessageType.INFO):
        d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=kind,buttons=Gtk.ButtonsType.NONE,text=title)
        d.format_secondary_text(text); d.add_button(self.t('close'),Gtk.ResponseType.CLOSE); d.run(); d.destroy()

    def choose_files(self,*_):
        if self.running or self.detecting:return
        d=Gtk.FileChooserDialog(title=self.t('add'),transient_for=self,action=Gtk.FileChooserAction.OPEN)
        d.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('add'),Gtk.ResponseType.OK); d.set_select_multiple(True)
        if d.run()==Gtk.ResponseType.OK: paths=d.get_filenames()
        else: paths=[]
        d.destroy()
        if paths:self.add_paths(paths)

    def choose_folder(self,*_):
        if self.running or self.detecting:return
        d=Gtk.FileChooserDialog(title=self.t('add_folder'),transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('choose'),Gtk.ResponseType.OK)
        path=d.get_filename() if d.run()==Gtk.ResponseType.OK else None;d.destroy()
        if path:self.apply_all.set_active(True);self.add_paths([path])

    def on_drag_motion(self,widget,context,x,y,time):
        if not self.running and not self.detecting:self.drop_box.get_style_context().add_class('drop-hover')
        return False
    def on_drag_leave(self,*_):self.drop_box.get_style_context().remove_class('drop-hover')

    def on_drop(self,widget,context,x,y,data,info,time):
        self.on_drag_leave()
        paths=[]
        for uri in data.get_uris():
            f=Gio.File.new_for_uri(uri)
            if f.get_path():paths.append(f.get_path())
        if not self.running and not self.detecting:self.add_paths(paths)
        Gtk.drag_finish(context,not self.running,False,time)

    def add_paths(self,paths):
        if self.running or self.detecting:return False
        self.detecting=True; self.set_controls(False); self.status.set_text(self.t('detecting')); self.progress.pulse()
        def worker():
            found=[]; errors=[]
            for path in core.expand_paths(paths):
                try:found.append(core.detect(path))
                except Exception as e:errors.append((str(path),e))
            GLib.idle_add(self.files_detected,found,errors)
        threading.Thread(target=worker,daemon=True).start()
        return False

    def files_detected(self,infos,errors):
        for info in infos:
            if any(item['info'].path==info.path for item in self.items.values()): continue
            ident=self.next_id; self.next_id+=1
            target='mp3' if info.kind=='audio' else 'mp4' if info.kind=='video' else 'txt' if info.kind=='pdf' or info.fmt=='srt' else 'pdf'
            self.items[ident]={'info':info,'target':target,'options':core.Options(),'result':None}
            icon=KIND_ICONS.get(info.kind,'text-x-generic') if not (info.kind=='document' and info.fmt in {'txt','md','rst','srt'}) else 'text-x-generic'
            self.model.append([ident,info.path.name,self.kind_label(info),target.upper(),self.t('pending'),'pending',icon])
        self.detecting=False; self.set_controls(True); self.status.set_text(self.t('idle')); self.progress.set_fraction(0)
        if len(self.model) and not self.tree.get_selection().get_selected()[1]:self.tree.get_selection().select_path(0)
        self.update_queue_view()
        if errors:
            text='\n'.join(Path(p).name+': '+self.error_text(e) for p,e in errors)
            self.logs.append(text); self.dialog(self.t('warning'),text,Gtk.MessageType.WARNING)
        return False

    def selection_changed(self,*_):self.refresh_selection();self.update_actions()
    def refresh_selection(self):
        model,itr=self.tree.get_selection().get_selected()
        self.current=model[itr][0] if itr else None
        self.empty.set_visible(self.current is None); self.options_box.set_visible(self.current is not None)
        if self.current is None:return
        self.options_box.set_no_show_all(False)
        self.options_box.show_all()
        self.options_box.set_no_show_all(True)
        item=self.items[self.current]; info=item['info']; self.loading_selection=True
        self.target_combo.remove_all()
        for target in core.targets(info):self.target_combo.append(target,target.upper())
        self.target_combo.set_active_id(item['target'])
        self.format_count.set_text(self.t('format_count').format(count=len(core.targets(info))))
        self.quality_combo.set_active_id(item['options'].quality); self.res_combo.set_active_id(item['options'].resolution)
        self.media_box.set_visible(info.kind=='video' and item['target'] in core.VIDEO); self.video_box.set_visible(info.kind=='video' and item['target'] in core.VIDEO)
        self.quality_box.set_visible(item['target']!='gif')
        self.audio_box.set_visible(False)
        key={'pdf':'pdf_hint','ebook':'ebook_hint','spreadsheet':'sheet_hint','presentation':'slides_hint','audio':'audio_hint','video':'video_hint'}.get(info.kind,'document_hint')
        text=self.t(key)
        if info.kind=='presentation' and item['target'] not in core.SLIDES:text=self.t('slides_text_hint')
        if info.kind=='spreadsheet' and item['target'] not in core.SHEET:text=self.t('sheet_text_hint')
        if item['target']=='gif':text+='\n\n'+self.t('gif_hint')
        self.text_box.set_visible(core.text_options_apply(info,item['target']))
        self.only_text.set_active(item['options'].only_text);self.use_ocr.set_active(item['options'].ocr);self.ocr_lang.set_active_id(item['options'].ocr_language);self.ocr_lang.set_sensitive(item['options'].ocr)
        if item['options'].only_text:text=self.t('only_text_hint')
        if item['options'].ocr:text+='\n\n'+self.t('ocr_hint')
        self.note.set_text(text); self.options_box.set_sensitive(not self.running)
        self.loading_selection=False

    def settings_changed(self,*_):
        if self.loading_selection or self.current is None:return
        item=self.items[self.current]
        item['target']=self.target_combo.get_active_id()
        item['options']=core.Options(self.quality_combo.get_active_id() or 'original',self.res_combo.get_active_id() or 'original','auto',self.only_text.get_active(),self.use_ocr.get_active(),self.ocr_lang.get_active_id() or 'tur+eng')
        for row in self.model:
            if row[0]==self.current:
                row[3]=item['target'].upper()
                if row[5]=='done': row[5]='pending'; row[4]=self.t('pending'); item['result']=None
        self.refresh_selection()

    def open_extras(self,*_):
        if self.running or self.detecting:return
        import subprocess,sys
        args=[sys.executable,'-m','donusturucu.extras','--lang',self.lang,'--output',str(self.output),'--theme',self.active_theme or 'light']
        if self.current in self.items:args+=['--source',str(self.items[self.current]['info'].path)]
        subprocess.Popen(args,cwd=str(Path(__file__).resolve().parents[1]),env=core.runtime.process_env())

    # ---- Queue actions -----------------------------------------------------
    def selected_result(self):
        if self.current not in self.items:return None
        result=self.items[self.current].get('result')
        return result if result and Path(result).exists() else None
    def open_selected_result(self,*_):
        result=self.selected_result()
        if result:self.launch_uri(Path(result).as_uri())
    def show_selected_result(self,*_):
        result=self.selected_result()
        if not result:return
        try:
            bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
            bus.call_sync('org.freedesktop.FileManager1','/org/freedesktop/FileManager1','org.freedesktop.FileManager1','ShowItems',
                GLib.Variant('(ass)',([Path(result).as_uri()],'')),None,Gio.DBusCallFlags.NONE,3000,None)
        except Exception:self.launch_uri(Path(result).parent.as_uri())
    def launch_uri(self,uri):
        try:Gio.AppInfo.launch_default_for_uri(uri,None)
        except Exception as e:self.dialog(self.t('error'),str(e),Gtk.MessageType.ERROR)
    def on_row_activated(self,tree,path,column):
        if self.selected_result():self.open_selected_result()
    def on_tree_button(self,tree,event):
        if event.type!=Gdk.EventType.BUTTON_PRESS or event.button!=3:return False
        hit=tree.get_path_at_pos(int(event.x),int(event.y))
        if not hit:return False
        tree.get_selection().select_path(hit[0])
        menu=Gio.Menu()
        if self.selected_result():
            menu.append(self.t('open_result'),'win.open-result'); menu.append(self.t('show_in_folder'),'win.show-result')
        if not self.running and not self.detecting:menu.append(self.t('remove'),'win.remove')
        if not menu.get_n_items():return True
        popover=Gtk.Popover.new_from_model(tree,menu)
        rect=Gdk.Rectangle(); rect.x,rect.y,rect.width,rect.height=int(event.x),int(event.y),1,1
        # Tree coordinates exclude the header; popovers are positioned against the widget.
        bx,by=tree.convert_bin_window_to_widget_coords(int(event.x),int(event.y)); rect.x,rect.y=bx,by
        popover.set_pointing_to(rect); popover.set_position(Gtk.PositionType.BOTTOM); popover.popup()
        return True

    def remove_item(self,*_):
        if self.running or self.detecting:return
        model,itr=self.tree.get_selection().get_selected()
        if itr:
            path=model.get_path(itr); del self.items[model[itr][0]]; model.remove(itr)
            if len(model):self.tree.get_selection().select_path(min(path.get_indices()[0],len(model)-1))
        self.start_button.set_sensitive(bool(len(self.model))); self.update_queue_view()
    def clear_items(self,*_):
        if self.running or self.detecting:return
        self.model.clear(); self.items.clear(); self.current=None; self.refresh_selection(); self.start_button.set_sensitive(False); self.progress.set_fraction(0); self.progress.set_show_text(False); self.update_queue_view()
    def choose_output(self,*_):
        d=Gtk.FileChooserDialog(title=self.t('choose'),transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('choose'),Gtk.ResponseType.OK)
        if self.output.exists():d.set_current_folder(str(self.output))
        if d.run()==Gtk.ResponseType.OK:
            self.output=Path(d.get_filename()); self.folder_label.set_text(str(self.output)); self.save_settings()
        d.destroy()
    def open_output(self,*_):
        try:self.output.mkdir(parents=True,exist_ok=True); Gio.AppInfo.launch_default_for_uri(self.output.as_uri(),None)
        except Exception as e:self.dialog(self.t('error'),str(e),Gtk.MessageType.ERROR)

    def set_controls(self,enabled):
        for w in (self.add_button,self.folder_add_button,self.remove_button,self.clear_button,self.folder_button,self.options_box,self.extras_button):w.set_sensitive(enabled)
        self.start_button.set_sensitive(enabled and bool(len(self.model)))
        if enabled:self.update_queue_view()
        else:self.update_actions()
    def row_status(self,ident,status):
        for row in self.model:
            if row[0]==ident:row[5]=status;row[4]=self.t(status)
        return False
    def update_progress(self,fraction):self.progress.set_fraction(max(0,min(1,fraction)));return False
    def progress_label(self,done):
        self.progress_done=done; self.progress.set_text(self.t('progress_files').format(done=done,total=self.progress_total)); return False

    def start(self,*_):
        if self.running or self.detecting:return
        if self.apply_all.get_active() and self.current in self.items:
            selected=self.items[self.current];target=selected['target'];options=selected['options']
            for ident,item in self.items.items():
                if target not in core.targets(item['info']):continue
                if item['target']!=target or item['options']!=options:
                    item['target']=target;item['options']=core.Options(**vars(options));item['result']=None
                    for row in self.model:
                        if row[0]==ident:row[3]=target.upper()
                    self.row_status(ident,'pending')
        todo=[row[0] for row in self.model if row[5]!='done']
        if not todo:return
        self.running=True; self.stopping=False; self.set_controls(False); self.stop_button.set_sensitive(True);self.progress.set_fraction(0)
        self.progress_total=len(todo); self.progress.set_show_text(True); self.progress_label(0)
        self.status.set_text(self.t('busy')); self.update_actions()
        # One runner covers the entire queue, so stopping between files is reliable.
        self.runner=core.Runner()
        def worker():
            counts={'done':0,'failed':0,'cancelled':0}
            for index,ident in enumerate(todo):
                if self.stopping:
                    counts['cancelled']+=1;GLib.idle_add(self.row_status,ident,'cancelled');continue
                item=self.items[ident];GLib.idle_add(self.row_status,ident,'running')
                self.runner.progress=lambda frac,i=index:GLib.idle_add(self.update_progress,(i+frac)/len(todo))
                try:
                    self.runner.notes.clear()
                    result=self.runner.convert(item['info'],item['target'],self.output,item['options']);item['result']=result
                    self.logs.append(f"✓ {item['info'].path}\n  → {result}\n")
                    for note in self.runner.notes:
                        if note[0]=='auto_ocr':self.logs.append('  ℹ '+self.t('auto_ocr').format(pages=note[1],total=note[2])+'\n')
                    state='done'
                except core.Cancelled:state='cancelled'
                except Exception as e:
                    state='failed';self.logs.append(f"✗ {item['info'].path}\n{self.error_text(e)}\n{getattr(e,'detail','')}\n")
                counts[state]+=1;GLib.idle_add(self.row_status,ident,state);GLib.idle_add(self.progress_label,index+1)
            GLib.idle_add(self.finished,counts)
        threading.Thread(target=worker,daemon=True).start()
        self.pulse_source=GLib.timeout_add(130,self.pulse)
    def pulse(self):
        if not self.running:return False
        if self.runner and self.current is not None:
            # Documents have no trustworthy percent indicator; animate while processing them.
            if any(row[5]=='running' and self.items[row[0]]['info'].kind not in {'audio','video'} for row in self.model):self.progress.pulse()
        return True
    def cancel(self,*_):
        if not self.running:return
        self.stopping=True
        if self.runner:self.runner.cancel()
        self.stop_button.set_sensitive(False); self.update_actions()
    def finished(self,counts):
        self.running=False;self.runner=None;self.stop_button.set_sensitive(False);self.set_controls(True)
        if self.pulse_source:GLib.source_remove(self.pulse_source);self.pulse_source=None
        self.progress.set_fraction(1 if not counts['cancelled'] else 0)
        summary=self.t('summary').format(**counts)
        self.status.set_text(summary+(' '+self.t('retry_hint') if counts['failed'] or counts['cancelled'] else ''));self.refresh_selection();self.update_actions()
        self.notify_finished(summary,counts)
        if counts['done'] and not counts['failed'] and not counts['cancelled']:
            self.status.set_text(self.t('complete')+' '+summary)
            d=Gtk.MessageDialog(transient_for=self,modal=False,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.NONE,text=self.t('complete'))
            d.format_secondary_text(summary);d.add_button(self.t('open'),Gtk.ResponseType.ACCEPT);d.add_button(self.t('close'),Gtk.ResponseType.CLOSE)
            d.set_default_response(Gtk.ResponseType.CLOSE)
            d.connect('response',self.on_completion_response);d.show_all();self.completion_dialog=d
        return False
    def on_completion_response(self,dialog,response):
        dialog.destroy()
        if response==Gtk.ResponseType.ACCEPT:self.open_output()
    def notify_finished(self,summary,counts):
        # Only notify when the window is in the background; the dialog covers the foreground case.
        app=self.get_application()
        if not app or self.is_active():return
        try:
            note=Gio.Notification.new(self.t('complete') if not counts['failed'] else self.t('error'))
            note.set_body(summary); note.set_icon(Gio.ThemedIcon.new('donusturucu'))
            app.send_notification('finished',note)
        except Exception:pass
    def error_text(self,e):
        if isinstance(e,core.ConversionError):return self.t(e.code)+((': '+e.detail) if e.code in {'missing_tool','unsupported','not_file'} and e.detail else '')
        return str(e)
    def show_log(self,*_):
        d=Gtk.Dialog(title=self.t('details'),transient_for=self,modal=True);d.set_default_size(760,430)
        d.add_button(self.t('close'),Gtk.ResponseType.CLOSE)
        text=Gtk.TextView();text.set_editable(False);text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);text.set_monospace(True);text.set_left_margin(10);text.set_top_margin(8)
        text.get_buffer().set_text('\n'.join(self.logs) or self.t('ready'))
        scroll=Gtk.ScrolledWindow();scroll.add(text);d.get_content_area().pack_start(scroll,True,True,0);d.show_all();d.run();d.destroy()
    def show_tools(self,*_):
        rows=[('✓ ' if exists else '✕ ')+name+' — '+self.t('available' if exists else 'missing') for name,exists in core.tools().items()]
        self.dialog(self.t('dependency_title'),'\n'.join(rows)+'\n\n'+self.t('dependency_hint'))
    def show_shortcuts(self,*_):self.dialog(self.t('shortcuts'),self.t('shortcut_list'))
    def show_about(self,*_):
        d=Gtk.AboutDialog(transient_for=self,modal=True); d.set_program_name(self.t('title'))
        d.set_comments(self.t('about_text')); d.set_logo_icon_name('donusturucu'); d.set_license_type(Gtk.License.GPL_3_0)
        d.run(); d.destroy()
    def on_close(self,*_):
        if self.running:
            d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.NONE,text=self.t('quit_title'))
            d.format_secondary_text(self.t('quit_text'));d.add_buttons(self.t('stay'),Gtk.ResponseType.CANCEL,self.t('quit'),Gtk.ResponseType.OK)
            result=d.run();d.destroy()
            if result!=Gtk.ResponseType.OK:return True
            self.cancel()
        self.save_settings();return False

class App(Gtk.Application):
    def __init__(self,paths):
        super().__init__(application_id='org.local.Donusturucu',flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.paths=paths
    def do_activate(self):
        win=self.get_active_window()
        if win:win.present()
        else:Window(self,self.paths)

def main():
    import sys
    paths=[str(Path(p).expanduser().resolve()) for p in sys.argv[1:]]
    return App(paths).run([sys.argv[0]])

if __name__=='__main__':main()
