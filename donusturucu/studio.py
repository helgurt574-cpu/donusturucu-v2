"""The desktop window (GTK 3), same look and tools as the Android app: home with drop zone and
file list, a workspace per file (preview, format ring, tool grid, options, Preview/Start),
history and settings. Conversions use core.Runner, classic edits operations.Editor and the
newer tools studio_ops.Studio."""
from __future__ import annotations
import json,os,shutil,tempfile,threading,time,traceback
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib,Gio,GdkPixbuf,Pango
from . import core,theme,runtime,VERSION,studio_ops as so,gtkui as ui,jobs
from .operations import Editor,Request,OperationError,actions as classic_actions
from .i18n import STRINGS

L={'convert':('Biçimini dönüştür','Formatê biguherîne','doc'),'watermark':('Filigran / logo sil','Nîşana avê rake','wand'),'denoise':('Sesi temizle','Dengê paqij bike','wave'),
 'compress':('Boyutu küçült','Biçûk bike','compress'),'pages':('Sayfa seç / sil / sırala','Rûpel hilbijêre / jê bibe','pages'),'pdf_rotate':('Sayfaları döndür','Rûpelan bizivirîne','rotate'),
 'edit':('Döndür / boyutlandır','Bizivirîne / mezinahî','rotate'),'images_pdf':('Fotoğraflardan PDF','PDF ji wêneyan','merge'),'ocr_image':('OCR ile metni çıkar','Bi OCRê nivîsê derxe','text'),
 'trim':('Kes','Bibire','cut'),'remove_range':('Bölüm sil','Beşekê rake','delete'),'split':('Parçala','Parçe bike','split'),'merge':('Birleştir','Yek bike','merge'),
 'mute_range':('Bölümün sesini kapat','Dengê beşekê bigire','mute'),'mute':('Sessiz yap','Bêdeng bike','mute'),'extract_audio':('Sesi çıkar','Deng derxe','audio'),
 'add_audio':('Ses ekle','Deng zêde bike','volume'),'replace_audio':('Sesi değiştir','Deng biguherîne','volume'),'frame':('Fotoğraf al','Wêne bistîne','camera'),'gif':('GIF oluştur','GIF çêke','gif'),
 'rotate':('Döndür','Bizivirîne','rotate'),'speed':('Hızı değiştir','Lezê biguherîne','speed'),'volume':('Ses düzeyi','Asta dengê','volume'),'fade_in':('Yavaşça yükselt','Hêdî bilind bike','volume'),
 'fade_out':('Yavaşça azalt','Hêdî kêm bike','volume'),'transcribe':('Konuşmayı yazıya dök','Axaftinê bike nivîs','mic'),'add_subtitle':('Altyazı ekle','Binnivîs zêde bike','subtitles'),
 'subtitle_text':('SRT → TXT (çeviri için)','SRT → TXT (ji bo wergerê)','subtitles'),'subtitle_restore':('Çevrilmiş TXT → SRT','TXT ya wergerandî → SRT','subtitles')}
NEW=jobs.NEW
FRONT={'video':['mp4','mkv','webm','mov','gif','mp3'],'audio':['mp3','wav','flac','m4a','ogg','opus'],'pdf':['docx','txt','png','jpg','epub','html'],'image':['jpg','png','webp','pdf','bmp'],
 'spreadsheet':['xlsx','pdf','csv','ods','docx','html'],'presentation':['pptx','pdf','odp','docx','txt','html']}
from .studio_text import ERRORS

def clock(s):s=int(round(s or 0));return f'{s//3600}:{s//60%60:02}:{s%60:02}' if s>=3600 else f'{s//60}:{s%60:02}'
def size(b):
    for unit,div in (('GB',1<<30),('MB',1<<20),('KB',1<<10)):
        if b>=div:return f'{b/div:.1f} {unit}' if unit!='KB' else f'{b/div:.0f} KB'
    return f'{b} B'

class Window(Gtk.ApplicationWindow):
    def __init__(self,app,paths):
        super().__init__(application=app,title='Dönüştürücü');self.set_default_size(1240,840);self.set_icon_name('donusturucu')
        s=theme.load_settings();self.settings=s
        self.ku=s.get('language','tr')=='ku';self.theme_mode=s.get('theme','system') if s.get('theme') in theme.MODES else 'system';self.accent=int(s.get('accent',0) or 0)
        self.output=Path(s.get('output',str(Path.home()/'Dönüştürülenler')))
        self.files=[];self.selected=-1;self.screen='home';self.built='';self.reset_file()
        self.busy=False;self.runner=None;self.status='';self.notice=None;self.log=[];self.show_log=False;self.progress_value=None
        self.last_outputs=[];self.summary=None;self.batch=False;self.portal_scheme=None
        self.css=Gtk.CssProvider();Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.watch_portal();self.resolve_look()
        root=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL);self.add(root)
        self.sidebar=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);self.sidebar.set_size_request(232,-1);self.cls(self.sidebar,'sidebar');root.pack_start(self.sidebar,False,False,0)
        self.scroll=Gtk.ScrolledWindow();self.scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);root.pack_start(self.scroll,True,True,0)
        self.page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.page.set_margin_start(32);self.page.set_margin_end(32);self.page.set_margin_top(26);self.page.set_margin_bottom(40)
        self.scroll.add(self.page)
        self.drag_dest_set(Gtk.DestDefaults.ALL,[Gtk.TargetEntry.new('text/uri-list',0,0)],Gdk.DragAction.COPY)
        self.connect('drag-data-received',self.on_drop);self.connect('drag-motion',self.on_drag_motion);self.connect('drag-leave',lambda *_:self.drop_hover(False))
        self.connect('delete-event',self.on_close)
        self.build();self.show_all()
        GLib.timeout_add_seconds(3,self.follow_system)
        if paths:self.add_paths(paths,open_single=True)

    # ------------------------------------------------------------- basics
    def t(self,tr,ku):return ku if self.ku else tr
    def cls(self,w,*names):
        for n in names:w.get_style_context().add_class(n)
        return w
    def label(self,text,css=None,wrap=True,xalign=0):
        l=Gtk.Label(label=text);l.set_xalign(xalign);l.set_line_wrap(wrap);l.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        if css:self.cls(l,*css.split())
        return l
    def box(self,vertical=True,spacing=8):return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,spacing=spacing)
    def card(self,spacing=10):return self.cls(self.box(True,spacing),'card')
    def button(self,text,icon=None,style='soft',callback=None,sensitive=True):
        b=Gtk.Button();self.cls(b,'pill',style);row=self.box(False,8);row.set_halign(Gtk.Align.CENTER)
        if icon:row.add(ui.icon(icon,{'primary':self.p['on_accent'],'soft':self.p['accent_text'],'danger':self.p['danger']}.get(style,self.p['text']),18))
        row.add(Gtk.Label(label=text));b.add(row)
        if callback:b.connect('clicked',lambda *_:callback())
        b.set_sensitive(sensitive);return b
    def icon_button(self,icon,callback,tip=None):
        b=Gtk.Button();self.cls(b,'icon');b.add(ui.icon(icon,self.p['text'],20));b.connect('clicked',lambda *_:callback())
        if tip:b.set_tooltip_text(tip)
        return b
    def chips(self,labels,selected,pick):
        f=ui.Flow()
        for i,text in enumerate(labels):
            b=Gtk.Button(label=('✓ ' if i==selected else '')+text);self.cls(b,'chip',*(['on'] if i==selected else []));b.set_sensitive(not self.busy)
            b.connect('clicked',lambda _b,i=i:pick(i));f.add_child(b)
        return f
    def choice(self,key,values,labels,default):
        cur=self.val(key,default);return self.chips(labels,values.index(cur) if cur in values else -1,lambda i:(self.put(key,values[i]),self.clear_preview(),self.build()))
    def toggles(self,keys,labels,defaults):
        f=ui.Flow()
        for k,text,d in zip(keys,labels,defaults):
            on=self.val(k,d)=='1';b=Gtk.Button(label=('✓ ' if on else '')+text);self.cls(b,'chip',*(['on'] if on else []));b.set_sensitive(not self.busy)
            b.connect('clicked',lambda _b,k=k,on=on:(self.put(k,'0' if on else '1'),self.clear_preview(),self.build()));f.add_child(b)
        return f
    def segmented(self,labels,selected,pick):
        row=self.cls(self.box(False,0),'seg')
        for i,text in enumerate(labels):
            b=Gtk.Button(label=text);self.cls(b,'seg-item',*(['on'] if i==selected else []));b.connect('clicked',lambda _b,i=i:pick(i));row.pack_start(b,True,True,0)
        return row
    def val(self,k,d):return self.vals.get(self.action+'.'+k,d)
    def put(self,k,v):self.vals[self.action+'.'+k]=v
    def field(self,key,title,default,hint,into):
        col=self.box(True,6);col.add(self.label(title,'caption'));e=Gtk.Entry();e.set_text(self.val(key,default));e.set_placeholder_text(hint);e.set_sensitive(not self.busy)
        e.connect('changed',lambda w:(self.put(key,w.get_text()),self.clear_preview(rebuild=False)));col.add(e);into.add(col);return e
    def times(self,into,with_end=True):
        row=self.box(False,12);a=self.box();self.field('start',self.t('Başlangıç','Destpêk'),'0','0:00',a);row.pack_start(a,True,True,0)
        if with_end:b=self.box();self.field('end',self.t('Bitiş · boşsa sona kadar','Dawî · vala be heta dawiyê'),'',self.t('sona kadar','heta dawiyê'),b);row.pack_start(b,True,True,0)
        into.add(row);into.add(self.label(self.t('Örnek: 15 = 15 saniye · 1:30 = 1 dakika 30 saniye.','Mînak: 15 = 15 çirke · 1:30 = 1 deqe û 30 çirke.'),'small'))
    def badge(self,name,size=40,fill=None,tint=None):
        fr=Gtk.EventBox();fr.set_size_request(size,size);bx=self.box();bx.set_valign(Gtk.Align.CENTER);bx.set_halign(Gtk.Align.CENTER);bx.add(ui.icon(name,tint or self.p['accent_text'],int(size*0.52)))
        prov=Gtk.CssProvider();prov.load_from_data(f'*{{background-color:{fill or self.p["accent_soft"]};border-radius:{int(size*0.3)}px;}}'.encode());fr.get_style_context().add_provider(prov,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+1)
        fr.add(bx);fr.set_halign(Gtk.Align.CENTER);fr.set_valign(Gtk.Align.CENTER);return fr

    # ------------------------------------------------------------- look
    def watch_portal(self):
        self.portal_scheme=theme._portal_scheme()
        try:
            bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
            bus.signal_subscribe('org.freedesktop.portal.Desktop','org.freedesktop.portal.Settings','SettingChanged','/org/freedesktop/portal/desktop',None,Gio.DBusSignalFlags.NONE,self.on_portal);self.bus=bus
        except Exception:pass
    def on_portal(self,conn,sender,path,iface,signal,params):
        namespace,key,value=params.unpack()
        if namespace=='org.freedesktop.appearance' and key=='color-scheme':
            try:self.portal_scheme=int(value)
            except (TypeError,ValueError):self.portal_scheme=None
            GLib.idle_add(self.relook)
    def follow_system(self):
        if self.theme_mode=='system' and theme.resolve('system',self.portal_scheme)!=('dark' if self.p['dark'] else 'light'):self.relook()
        return True
    def resolve_look(self):
        dark=theme.resolve(self.theme_mode,self.portal_scheme)=='dark';self.p=ui.palette(dark,self.accent)
        settings=Gtk.Settings.get_default()
        if settings.props.gtk_theme_name!='Adwaita':settings.props.gtk_theme_name='Adwaita'
        settings.props.gtk_application_prefer_dark_theme=dark;self.css.load_from_data(ui.css(self.p))
    def relook(self):self.resolve_look();self.drop_cache();self.built='';self.build();return False
    def save(self):
        self.settings.update(language='ku' if self.ku else 'tr',theme=self.theme_mode,accent=self.accent,output=str(self.output))
        try:
            path=theme.settings_path();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(self.settings,ensure_ascii=False,indent=1),encoding='utf-8')
        except OSError:pass

    # ------------------------------------------------------------- frame
    def build(self):
        same=self.screen==self.built;adj=self.scroll.get_vadjustment();keep=adj.get_value()
        if self.screen!='work':
            for pl in list(ui.Player.live):
                if pl.playing:pl.pause()
        self.set_title(self.t('Dönüştürücü','Veguherîner'))
        for c in self.sidebar.get_children():self.sidebar.remove(c)
        self.fill_sidebar()
        height=self.page.get_allocated_height()
        for c in self.page.get_children():self.page.remove(c)
        self.page.set_size_request(-1,height if same else -1)
        self.status_label=None;self.progress_bar=None;self.region_note=None
        if self.screen=='work' and self.source is not None:self.build_work()
        elif self.screen=='history':self.build_history()
        elif self.screen=='settings':self.build_settings()
        else:self.screen='home';self.build_home()
        self.built=self.screen;self.page.show_all();self.sidebar.show_all()
        if same:GLib.idle_add(adj.set_value,keep)
        else:adj.set_value(0);self.page.set_size_request(-1,-1)
        return False
    def go(self,where):
        if where!='home':self.notice=None
        self.screen=where;self.build()
    def fill_sidebar(self):
        brand=self.box(False,10);brand.set_margin_bottom(18);brand.set_margin_start(6);brand.add(ui.pie_logo(40))
        col=self.box(True,0);col.add(self.label(self.t('Dönüştürücü','Veguherîner'),'brand'));col.add(self.label(self.t('Seç · önizle · dönüştür','Hilbijêre · pêşdîtin · veguherîne'),'brand-sub'));brand.add(col)
        self.sidebar.add(brand)
        for key,icon,text in [('home','home',self.t('Ana sayfa','Destpêk')),('history','history',self.t('Geçmiş','Dîrok')),('settings','tune',self.t('Ayarlar','Mîheng'))]:
            on=self.screen==key or (key=='home' and self.screen=='work')
            b=Gtk.Button();self.cls(b,'nav',*(['on'] if on else []));row=self.box(False,12);row.add(ui.icon(icon,self.p['accent_text'] if on else self.p['text'],20));row.add(Gtk.Label(label=text));b.add(row)
            b.connect('clicked',lambda _b,k=key:self.go(k));self.sidebar.add(b)
        if self.files:
            self.sidebar.add(self.label(self.t('Dosyalar','Dosye'),'caption'))
            for i,f in enumerate(self.files[:12]):
                on=self.screen=='work' and i==self.selected;b=Gtk.Button();self.cls(b,'nav',*(['on'] if on else []))
                l=Gtk.Label(label=f['info'].path.name);l.set_ellipsize(Pango.EllipsizeMode.MIDDLE);l.set_xalign(0);l.set_max_width_chars(22)
                row=self.box(False,10);row.add(ui.icon(self.kind_icon(f['info']),self.p['accent_text'] if on else self.p['muted'],16));row.add(l);b.add(row)
                b.connect('clicked',lambda _b,i=i:self.select(i));self.sidebar.add(b)
        spacer=Gtk.Box();spacer.set_vexpand(True);self.sidebar.add(spacer)
        if self.busy:
            p=Gtk.ProgressBar();p.set_fraction(self.progress_value or 0)
            if self.progress_value is None:p.pulse()
            self.side_progress=p;self.sidebar.add(p)
        self.sidebar.add(self.label('Linux · '+VERSION,'small'))

    # ------------------------------------------------------------- home
    def build_home(self):
        self.page.add(self.label(self.t('Ana sayfa','Destpêk'),'title'))
        drop=self.box(True,10);self.cls(drop,'drop');drop.set_halign(Gtk.Align.FILL);self.drop_box=drop
        ev=Gtk.EventBox();ev.add(drop);ev.connect('button-release-event',lambda *_:None if self.busy else self.choose_files())
        circle=self.badge('upload',64);drop.add(circle)
        h=self.label(self.t('Dosyaları buraya sürükle','Dosyeyan bikişîne vir'),'head',xalign=0.5);drop.add(h)
        drop.add(self.label(self.t('Video, ses, PDF, belge veya fotoğraf. Dosya yöneticisinden sürükleyip bırakabilir ya da aşağıdan seçebilirsin.','Vîdyo, deng, PDF, belge an wêne. Ji rêveberê dosyeyan bikişîne û berde an jêr hilbijêre.'),'muted',xalign=0.5))
        row=self.box(False,10);row.set_halign(Gtk.Align.CENTER);row.set_margin_top(6)
        row.add(self.button(self.t('Dosya seç','Dosye hilbijêre'),'add','primary',self.choose_files,not self.busy));row.add(self.button(self.t('Klasör ekle','Peldankê zêde bike'),'folder','soft',self.choose_folder,not self.busy))
        drop.add(row);self.page.add(ev)
        self.status_box(self.page,False)
        if self.files:
            head=self.box(False);head.set_margin_top(14);head.pack_start(self.label(self.t('Dosyalar','Dosye')+f' · {len(self.files)}','section'),True,True,0)
            head.add(self.button(self.t('Listeyi temizle','Lîsteyê paqij bike'),None,'plain',self.clear_files,not self.busy));self.page.add(head)
            grid=Gtk.FlowBox();grid.set_selection_mode(Gtk.SelectionMode.NONE);grid.set_max_children_per_line(3);grid.set_min_children_per_line(1);grid.set_column_spacing(10);grid.set_row_spacing(10);grid.set_homogeneous(True)
            for i,f in enumerate(self.files):grid.add(self.file_row(i,f))
            self.page.add(grid);self.page.add(self.label(self.t('Listeden kaldırmak orijinal dosyayı silmez.','Rakirin ji lîsteyê dosyeya resen jê nabe.'),'small'))
        hist=self.history()
        head=self.box(False);head.set_margin_top(14);head.pack_start(self.label(self.t('Son dönüştürmeler','Veguherînên dawî'),'section'),True,True,0)
        if hist:head.add(self.button(self.t('Tümü','Hemû'),None,'plain',lambda:self.go('history')))
        self.page.add(head)
        if not hist:self.page.add(self.label(self.t('Dönüştürdüğün dosyalar burada görünür.','Dosyeyên ku tu diguherînî li vir xuya dibin.'),'muted'))
        for h in hist[:4]:self.page.add(self.history_row(h))
    def file_row(self,i,f):
        ev=Gtk.EventBox();row=self.cls(self.box(False,12),'row-card');ev.add(row);ev.connect('button-release-event',lambda *_:self.select(i))
        row.add(self.thumb(f.get('thumb'),self.kind_icon(f['info']),52));col=self.box(True,2)
        name=Gtk.Label(label=f['info'].path.name);name.set_xalign(0);name.set_ellipsize(Pango.EllipsizeMode.MIDDLE);self.cls(name,'section');col.add(name);col.add(self.label(self.meta(f['info']),'small',False))
        row.pack_start(col,True,True,0);row.add(self.icon_button('close',lambda:self.remove_file(i),self.t('Listeden kaldır','Ji lîsteyê rake')));return ev
    def thumb(self,path,icon,size):
        if path and Path(path).is_file():
            try:
                pb=GdkPixbuf.Pixbuf.new_from_file(str(path));s=max(size/pb.get_width(),size/pb.get_height());pb=pb.scale_simple(max(1,int(pb.get_width()*s)),max(1,int(pb.get_height()*s)),GdkPixbuf.InterpType.BILINEAR)
                x=(pb.get_width()-size)//2;y=(pb.get_height()-size)//2;pb=pb.new_subpixbuf(max(0,x),max(0,y),min(size,pb.get_width()),min(size,pb.get_height()))
                area=Gtk.DrawingArea();area.set_size_request(size,size)
                def draw(w,cr,pb=pb):ui._round_rect(cr,0,0,size,size,12);cr.clip();Gdk.cairo_set_source_pixbuf(cr,pb,0,0);cr.paint()
                area.connect('draw',draw);return area
            except Exception:pass
        return self.badge(icon,size)
    @staticmethod
    def kind_icon(info):return {'video':'video','audio':'audio','image':'image','pdf':'doc'}.get(info.kind,'subtitles' if info.fmt=='srt' else 'doc')
    def kind_name(self,info):
        return {'video':self.t('Video','Vîdyo'),'audio':self.t('Ses','Deng'),'image':self.t('Fotoğraf','Wêne'),'pdf':'PDF'}.get(info.kind,info.fmt.upper())
    def meta(self,info):
        parts=[self.kind_name(info)]
        if info.kind in ('video','audio'):parts.append(clock(info.duration))
        if info.width and info.kind in ('video','image'):parts.append(f'{info.width}×{info.height}')
        try:parts.append(size(info.path.stat().st_size))
        except OSError:pass
        return ' · '.join(parts)

    # ------------------------------------------------------------- files
    def choose_files(self):
        d=Gtk.FileChooserNative.new(self.t('Dosya seç','Dosye hilbijêre'),self,Gtk.FileChooserAction.OPEN,None,None);d.set_select_multiple(True)
        if d.run()==Gtk.ResponseType.ACCEPT:self.add_paths(d.get_filenames(),open_single=True)
    def choose_folder(self):
        d=Gtk.FileChooserNative.new(self.t('Klasör ekle','Peldankê zêde bike'),self,Gtk.FileChooserAction.SELECT_FOLDER,None,None)
        if d.run()==Gtk.ResponseType.ACCEPT:self.add_paths(d.get_filenames())
    def pick_other(self):
        d=Gtk.FileChooserNative.new(self.t('İkinci dosyayı seç','Dosyeya duyem hilbijêre'),self,Gtk.FileChooserAction.OPEN,None,None)
        if d.run()!=Gtk.ResponseType.ACCEPT:return
        try:self.other=so.detect(d.get_filename())
        except Exception as e:self.fail(e);return
        self.clear_preview();self.build()
    def on_drag_motion(self,*args):self.drop_hover(True);return False
    def drop_hover(self,on):
        box=getattr(self,'drop_box',None)
        if box is not None:(box.get_style_context().add_class if on else box.get_style_context().remove_class)('hover')
    def on_drop(self,w,ctx,x,y,data,info,time_):
        self.drop_hover(False);paths=[]
        for uri in data.get_uris() or []:
            f=Gio.File.new_for_uri(uri)
            if f.get_path():paths.append(f.get_path())
        if paths:self.add_paths(paths,open_single=len(paths)==1)
    def add_paths(self,paths,open_single=False):
        if self.busy:return
        self.busy=True;self.set_status(self.t('Dosyalar ekleniyor…','Dosye tên zêdekirin…'));self.build()
        def work():
            found=[];errors=0
            for path in core.expand_paths(paths):
                try:
                    info=so.detect(path);found.append({'info':info,'thumb':self.make_thumb(info)})
                    GLib.idle_add(self.set_status,self.t('Ekleniyor: ','Tê zêdekirin: ')+str(len(found)))
                except Exception as e:errors+=1;self.log.append(f'✗ {path}: {self.error_text(e)}')
            GLib.idle_add(self.added,found,errors,open_single)
        threading.Thread(target=work,daemon=True).start()
    def added(self,found,errors,open_single):
        self.busy=False;self.files+=found
        self.status=self.t('Listeye eklendi: ','Li lîsteyê zêde bûn: ')+str(len(found))+(self.t(' · Eklenemeyen: ',' · Nehatin zêdekirin: ')+str(errors) if errors else '')
        self.notice=self.status+('\n'+'\n'.join(self.log[-errors:]) if errors else '') if errors else None
        if len(found)==1 and (open_single or len(self.files)==1):self.select(len(self.files)-1)
        else:self.go('home')
        return False
    def make_thumb(self,info):
        try:
            folder=Path(tempfile.gettempdir())/'donusturucu-thumbs';folder.mkdir(exist_ok=True);out=folder/f'{abs(hash(str(info.path)))}-{int(time.time()*1000)}.png'
            st=so.Studio()
            if info.kind=='video':st.still(info.path,min(1,info.duration*0.1),240,out)
            elif info.kind=='image':st.ff([*st.inp(info.path),'-frames:v','1','-vf',"scale='min(240,iw)':-2",str(out)])
            elif info.kind=='pdf':return st.render_page(info.path,0,200,folder)
            else:return None
            return out
        except Exception:return None
    def remove_file(self,i):
        if self.busy:return
        self.files.pop(i)
        if self.selected==i:self.selected=-1;self.reset_file()
        elif self.selected>i:self.selected-=1
        self.build()
    def clear_files(self):
        if self.busy:return
        self.files.clear();self.selected=-1;self.reset_file();self.build()
    def reset_file(self):
        self.source=None;self.other=None;self.action='convert';self.target='';self.tools_tab=False;self.donut_back=False;self.vals={};self.regions=[]
        self.base=None;self.pdf_page=0;self.pdf_count=0;self.frame_at=-1;self.peaks=None;self.excerpt=None;self.preview=None;self.summary=None;self.load_token=0
        self.quality='original';self.resolution='original';self.only_text=False;self.ocr=False;self.ocr_lang='tur+eng';self.drop_cache()
    def drop_cache(self):
        ui.Player.stop_all();self.source_view=None;self.source_key=None;self.preview_view=None;self.preview_key=None;self.source_picture=None;self.source_player=None;self.page_label=None
    def select(self,i):
        if self.busy:return
        self.reset_file();self.selected=i;self.source=self.files[i]['info'];self.screen='work';self.status='';self.build();self.load_base()

    # ------------------------------------------------------------- workspace
    def actions(self):return jobs.tools_for(self.source)
    def action_label(self,a):
        tr,ku,icon=L.get(a,(a,a,'doc'));info=self.source
        if a=='compress':tr,ku=("PDF'yi küçült",'PDFê biçûk bike') if info.kind=='pdf' else ('Videoyu küçült','Vîdyoyê biçûk bike')
        if a=='trim' and info.kind in ('video','audio'):tr,ku=('Video kes','Vîdyoyê bibire') if info.kind=='video' else ('Ses kes','Dengê bibire')
        if a=='split' and info.kind not in ('video','audio'):tr,ku=("Sayfalara ayır",'Li rûpelan parçe bike')
        return (ku if self.ku else tr),icon
    def build_work(self):
        info=self.source;head=self.box(False,12);head.add(self.icon_button('back',lambda:self.go('home'),self.t('Geri','Paş')))
        col=self.box(True,2);name=Gtk.Label(label=info.path.name);name.set_xalign(0);name.set_ellipsize(Pango.EllipsizeMode.MIDDLE);self.cls(name,'head');col.add(name);col.add(self.label(self.meta(info),'small',False))
        head.pack_start(col,True,True,0);self.page.add(head)
        cols=self.box(False,24);self.page.add(cols)
        left=self.box(True,12);left.set_size_request(420,-1);right=self.box(True,12);right.set_size_request(470,-1)
        cols.pack_start(left,True,True,0);cols.pack_start(right,True,True,0)
        key=self.source_key_now()
        if self.source_view is None or key!=self.source_key:self.source_view=self.source_card();self.source_key=key
        self.adopt(left,self.source_view)
        if self.source_player is not None:self.source_player.show_marks(self.tools_tab and self.action in self.TIMED)
        acts=self.actions()
        right.add(self.segmented([self.t('Dönüştür','Veguherîne'),self.t('Araçlar','Amûr')+f' · {len(acts)-1}'],1 if self.tools_tab else 0,self.pick_tab))
        if not self.tools_tab:self.action='convert';right.add(self.convert_card())
        else:
            right.add(self.tool_grid(acts))
            if self.action and self.action!='convert':right.add(self.options_card())
        if not self.action:return
        if len(self.files)>1:
            c=Gtk.CheckButton(label=self.t('Listedeki uygun bütün dosyalara uygula','Li hemû pelên guncav ên lîsteyê bi kar bîne')+f' ({len(self.files)})');c.set_active(self.batch);c.set_sensitive(not self.busy)
            c.connect('toggled',lambda w:setattr(self,'batch',w.get_active()));right.add(c)
        row=self.box(False,10)
        row.pack_start(self.button(self.t('Önizle','Pêşdîtin'),'eye','soft',self.run_preview,not self.busy and self.previewable()),True,True,0)
        row.pack_start(self.button(self.t('Başlat','Dest pê bike'),'play','primary',self.start,not self.busy),True,True,0);right.add(row)
        right.add(self.label(self.t('Kayıt klasörü: ','Peldanka tomarkirinê: ')+str(self.output),'small'))
        self.status_box(right,True)
        pkey=(id(self.preview),self.preview.get('show')) if self.preview and self.preview['action']==self.action else None
        if pkey is None:self.preview_view=None
        elif self.preview_view is None or pkey!=self.preview_key:self.preview_view=self.preview_card();self.preview_key=pkey
        if self.preview_view is not None:self.adopt(left,self.preview_view)
        if self.summary:right.add(self.result_card())
        b=self.button(self.t('İşlem ayrıntılarını gizle','Hûrgiliyan veşêre') if self.show_log else self.t('İşlem ayrıntılarını göster','Hûrgiliyan nîşan bide'),'info','plain',lambda:(setattr(self,'show_log',not self.show_log),self.build()))
        right.add(b)
        if self.show_log:
            tv=Gtk.TextView();tv.set_editable(False);tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);tv.get_buffer().set_text('\n'.join(self.log[-200:]) or '—');self.cls(tv,'mono');right.add(tv)
    @staticmethod
    def adopt(box,widget):
        """Kept widgets (picture, preview) move into the new layout instead of being rebuilt."""
        parent=widget.get_parent()
        if parent is not None:parent.remove(widget)
        box.add(widget)
    def pick_tab(self,i):
        if self.busy:return
        self.tools_tab=i==1;self.action='convert' if not self.tools_tab else ''
        self.clear_preview(rebuild=False);self.build()
    def marking(self):return self.action=='watermark' and self.source.kind in ('video','image','pdf')
    def paged(self):
        """Files shown page by page: PDFs and documents (turned into PDF for viewing)."""
        info=self.source;return info.kind=='pdf' or (info.kind in ('document','spreadsheet','presentation','ebook') and info.fmt!='srt')
    def source_key_now(self):
        # The picture, page and frame change in place (with a fade); only these rebuild the card.
        info=self.source
        return (str(info.path),self.marking(),self.base is not None,self.pdf_count>0,self.peaks is not None,self.excerpt,self.region_version if self.marking() else 0,self.p['accent'],self.p['dark'])
    region_version=0
    def source_card(self):
        info=self.source;c=self.card(10);self.source_picture=None;self.source_player=None;self.page_label=None
        if info.kind=='audio':
            self.source_player=ui.Player(self.p,info.path,info.duration,peaks=self.peaks or [],marks=self.mark_time,labels=self.mark_labels())
            c.add(self.source_player)
            if self.peaks is None:c.add(self.label(self.t('Ses dalgası hazırlanıyor…','Pêla dengê tê amadekirin…'),'small'))
            return c
        if info.kind=='video' and not self.marking():
            self.source_player=ui.Player(self.p,info.path,info.duration,size=so.shown_size(info),poster=self.base,marks=self.mark_time,labels=self.mark_labels())
            self.source_picture=self.source_player.view;c.add(self.source_player);return c
        if self.base is None:
            if self.excerpt is not None and not self.paged() and info.kind not in ('video','image'):
                t=self.label(self.excerpt,'mono');t.set_selectable(True);c.add(t);return c
            w=self.box(True,10);w.set_size_request(-1,260);w.set_valign(Gtk.Align.CENTER);b=self.badge(self.kind_icon(info),64);b.set_margin_top(70);w.add(b)
            wait=self.t('Belge sayfaları hazırlanıyor…','Rûpelên belgeyê tên amadekirin…') if self.paged() and info.kind!='pdf' else self.t('Önizleme hazırlanıyor…','Pêşdîtin tê amadekirin…')
            w.add(self.label(self.excerpt or wait,'muted',xalign=0.5));c.add(w);return c
        marking=self.marking()
        pic=ui.Picture(self.p,self.base,ui.Picture.SELECT if marking else ui.Picture.VIEW,self.regions,changed=self.regions_changed,height=560 if self.paged() else 420)
        self.source_picture=pic;c.add(pic)
        if marking:
            c.add(self.label(self.t('İsteğe bağlı: otomatik bulunamayan filigranın üstünü çerçevele; o alan her sayfada çevresinin rengiyle kapatılır.','Ne mecbûrî: li ser nîşana avê çarçove bike; ew qad li her rûpelê tê girtin.') if info.kind=='pdf' else self.t('Filigranın ya da logonun üstünü fareyle çerçevele. Köşelerden boyutlandır, içinden taşı. En fazla 4 alan.','Li ser nîşana avê an logoyê bi mişkê çarçove bike. Ji goşeyan mezin bike, ji navê bikişîne. Herî zêde 4 qad.'),'small'))
            row=self.box(False,10);row.add(self.button(self.t('Alanları temizle','Qadan paqij bike'),'close','plain',self.clear_regions))
            if info.kind=='video':row.add(self.button(self.t('Başka kare','Kareke din'),'camera','soft',self.next_frame))
            c.add(row)
        if self.paged() and self.pdf_count>0:
            nav=self.box(False,8);nav.set_halign(Gtk.Align.CENTER)
            nav.add(self.icon_button('chevron_left',lambda:self.turn_page(-1),self.t('Önceki sayfa','Rûpela berê')))
            self.page_label=self.label(self.page_text(),'section',False,0.5);nav.add(self.page_label)
            nav.add(self.icon_button('chevron',lambda:self.turn_page(1),self.t('Sonraki sayfa','Rûpela din')));c.add(nav)
        return c
    def page_text(self):return self.t('Sayfa ','Rûpel ')+f'{self.pdf_page+1} / {self.pdf_count}'
    TIMED={'trim','remove_range','split','mute_range','gif','frame','rotate','speed','volume','fade_in','fade_out','extract_audio','transcribe','add_audio','replace_audio'}
    def mark_labels(self):return (self.t('Başlangıç = bu an','Destpêk = niha'),self.t('Bitiş = bu an','Dawî = niha'))
    def mark_time(self,key,pos):
        """Start/end of the chosen tool taken from where the player stands."""
        if self.action not in self.TIMED:return
        if self.action=='frame':key='start'
        self.put(key,ui.clock(pos,True));self.clear_preview(rebuild=False);self.build()
        self.set_status((self.t('Başlangıç: ','Destpêk: ') if key=='start' else self.t('Bitiş: ','Dawî: '))+ui.clock(pos,True))
    def regions_changed(self,regions):
        self.regions=regions;self.preview=None;self.preview_view=None
        if self.region_note is not None:self.region_note.set_text(self.region_text())
    def clear_regions(self):self.regions=[];self.region_version+=1;self.clear_preview(rebuild=False);self.build()
    def next_frame(self):
        at=self.frame_at if self.frame_at>=0 else min(1,self.source.duration*0.1);self.frame_at=(at+max(1,self.source.duration/6))%max(1,self.source.duration);self.load_base()
    def turn_page(self,d):
        n=self.pdf_page+d
        if not 0<=n<self.pdf_count:return
        self.pdf_page=n
        if self.page_label is not None:self.page_label.set_text(self.page_text())
        if self.preview is not None:self.clear_preview(rebuild=False);self.build()
        self.load_base()
    def region_text(self):
        if self.source.kind=='pdf':return self.t('Alan seçilmedi (isteğe bağlı).','Qad nehatiye hilbijartin (ne mecbûrî).') if not self.regions else self.t('Seçili alan: ','Qadên hilbijartî: ')+f'{len(self.regions)}'+self.t(' · her sayfada kapatılır',' · li her rûpelê tê girtin')
        return self.t('Henüz alan seçilmedi.','Hîn qad nehatiye hilbijartin.') if not self.regions else '✓ '+self.t('Seçili alan: ','Qadên hilbijartî: ')+str(len(self.regions))
    def view_pdf(self,info,entry):
        """The PDF to show for a file; documents are converted once and kept for the session."""
        if info.kind=='pdf':return info.path
        cached=entry.get('pdf')
        if cached and Path(cached).is_file():return Path(cached)
        folder=Path(tempfile.mkdtemp(prefix='donustur-view-'));out=core.Runner().convert(info,'pdf',folder,core.Options(only_text=False))
        entry['pdf']=str(out);return out
    def load_base(self):
        self.load_token+=1;token=self.load_token;info=self.source;page=self.pdf_page;at=self.frame_at;entry=self.files[self.selected] if 0<=self.selected<len(self.files) else {}
        paged=self.paged()
        def work():
            base=peaks=excerpt=None;count=self.pdf_count
            try:
                st=so.Studio();folder=Path(tempfile.mkdtemp(prefix='donustur-base-'))
                if info.kind=='video':out=st.still(info.path,at if at>=0 else min(1,info.duration*0.1),1400,folder/'frame.png');base=GdkPixbuf.Pixbuf.new_from_file(str(out))
                elif info.kind=='audio':peaks=st.peaks(info.path,120)
                elif paged:
                    pdf=self.view_pdf(info,entry)
                    if not count:count=len(st.reader(pdf).pages)
                    base=GdkPixbuf.Pixbuf.new_from_file(str(st.render_page(pdf,min(page,max(0,count-1)),1100,folder)))
                elif info.kind=='image':base=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(st.still_png(info.path,folder)),1800,1800,True)
                else:
                    text=info.path.read_text(encoding='utf-8',errors='replace');excerpt=text[:4000]+('…' if len(text)>4000 else '')
                shutil.rmtree(folder,ignore_errors=True)
            except Exception as e:excerpt=self.t('Önizleme hazırlanamadı: ','Pêşdîtin nehat amadekirin: ')+self.error_text(e);self.log.append(traceback.format_exc()[-1200:])
            GLib.idle_add(self.base_ready,token,info,base,peaks,excerpt,count)
        threading.Thread(target=work,daemon=True).start()
    def base_ready(self,token,info,base,peaks,excerpt,count):
        if token!=self.load_token or info is not self.source:return False
        had=self.base is not None;self.pdf_count=count;self.peaks=peaks if peaks is not None else self.peaks
        if had and base is not None and self.source_picture is not None and excerpt is None and self.screen=='work':
            # Next page or another frame: fade the new picture in over the current one, nothing else moves.
            self.base=base;self.source_picture.crossfade(base)
            if self.page_label is not None:self.page_label.set_text(self.page_text())
            return False
        self.base=base;self.excerpt=excerpt
        if self.screen=='work':self.build()
        return False

    # -- convert
    def formats(self):
        all_=so.convert_targets(self.source);pref=FRONT.get(self.source.kind,['pdf','docx','txt','odt','epub','html'])
        front=[f for f in pref if f in all_][:6];rest=[f for f in all_ if f not in front];return front,rest
    def convert_card(self):
        c=self.card(10);info=self.source;front,back=self.formats()
        if self.target not in front+back:self.target=front[0] if front else back[0]
        c.add(self.label(self.t('Neye dönüştürülsün?','Bibe çi formatê?'),'head'))
        if back:c.add(self.segmented([self.t('Sık kullanılan ','Yên pir ')+str(len(front)),self.t('Diğer ','Yên din ')+str(len(back))],1 if self.donut_back else 0,self.flip_side))
        src={'video':self.t('video','vîdyo'),'audio':self.t('ses','deng'),'image':self.t('fotoğraf','wêne')}.get(info.kind,info.fmt.upper())
        count=len(self.files) if self.batch else 1
        d=ui.Donut(self.p,[f.upper() for f in front],[f.upper() for f in back],self.target.upper(),f'{count} {src}','→ '+self.target.upper(),self.donut_back,self.pick_format,self.donut_flipped)
        if getattr(self,'animate_donut',False):self.animate_donut=False;d.animate()
        c.add(d)
        if back:c.add(self.label(self.t('Diğer biçimler için ortaya tıkla.','Ji bo formatên din li navendê bitikîne.'),'small',xalign=0.5))
        f=self.target
        if info.kind=='video' and f in core.VIDEO and f!='gif':
            c.add(self.label(self.t('Video kalitesi','Kalîteya vîdyoyê'),'caption'))
            qs=['original','high','balanced','small'];c.add(self.chips([self.t('Orijinal','Resen'),self.t('Yüksek','Bilind'),self.t('Dengeli','Hevseng'),self.t('Küçük dosya','Dosyeya biçûk')],qs.index(self.quality),lambda i:(setattr(self,'quality',qs[i]),self.clear_preview(),self.build())))
            c.add(self.label(self.t('Çözünürlük','Çareserî'),'caption'))
            rs=['original','1080','720','480'];c.add(self.chips([self.t('Aynı','Wek xwe'),'1080p','720p','480p'],rs.index(self.resolution),lambda i:(setattr(self,'resolution',rs[i]),self.clear_preview(),self.build())))
        if info.kind=='image':
            if f not in ('png','bmp'):c.add(self.label(self.t('Kalite','Kalîte'),'caption'));c.add(self.choice('q',['1','2','3'],[self.t('Yüksek','Bilind'),self.t('Dengeli','Hevseng'),self.t('Küçük dosya','Dosyeya biçûk')],'2'))
            c.add(self.label(self.t('Boyut','Mezinahî'),'caption'));c.add(self.choice('scale',['100','75','50','25'],['%100','%75','%50','%25'],'100'))
            c.add(self.label(self.t('Renk','Reng'),'caption'));c.add(self.choice('gray',['0','1'],[self.t('Renkli','Rengîn'),self.t('Siyah-beyaz','Reş û spî')],'0'))
        if info.kind=='pdf' and f in so.PDF_IMAGE:c.add(self.label(self.t('Çözünürlük (her sayfa ayrı resim olur)','Çareserî (her rûpel dibe wêneyek)'),'caption'));c.add(self.choice('dpi',['96','150','300'],['96 DPI','150 DPI','300 DPI'],'150'))
        if core.text_options_apply(info,f):
            c.add(self.label(self.t('Belge seçenekleri','Vebijarkên belgeyê'),'caption'))
            c.add(self.flags_row())
            if self.ocr:
                langs=['tur+eng','tur','eng','kmr','ara','fas'];c.add(self.chips(['Türkçe + English','Türkçe','English','Kurmancî','العربية','فارسی'],langs.index(self.ocr_lang) if self.ocr_lang in langs else 0,lambda i:(setattr(self,'ocr_lang',langs[i]),self.build())))
        hints={'pdf':'pdf_hint','ebook':'ebook_hint','spreadsheet':'sheet_hint','presentation':'slides_hint','audio':'audio_hint','video':'video_hint'}
        key=hints.get(info.kind,'document_hint') if info.kind!='image' else None
        if key and key in STRINGS['ku' if self.ku else 'tr']:c.add(self.label(STRINGS['ku' if self.ku else 'tr'][key],'small'))
        return c
    def flags_row(self):
        f=ui.Flow()
        for text,attr in [(self.t('Yalnızca metin','Tenê nivîs'),'only_text'),(self.t('OCR: taranmış sayfaları oku','OCR: rûpelên skankirî bixwîne'),'ocr')]:
            on=getattr(self,attr);b=Gtk.Button(label=('✓ ' if on else '')+text);self.cls(b,'chip',*(['on'] if on else []));b.connect('clicked',lambda _b,a=attr:(setattr(self,a,not getattr(self,a)),self.clear_preview(),self.build()));f.add_child(b)
        return f
    def flip_side(self,i):
        if (i==1)!=self.donut_back:self.donut_back=i==1;self.animate_donut=True;self.build()
    def donut_flipped(self,back):self.donut_back=back;self.animate_donut=False;GLib.idle_add(self.build)
    def pick_format(self,f):
        if self.busy:return
        self.target=f.lower();self.clear_preview(rebuild=False);GLib.idle_add(self.build)

    # -- tools
    def tool_grid(self,acts):
        grid=Gtk.Grid();grid.set_column_homogeneous(True);grid.set_column_spacing(8);grid.set_row_spacing(8);n=0
        for a in acts:
            if a=='convert':continue
            text,icon=self.action_label(a);on=a==self.action
            b=Gtk.Button();self.cls(b,'tile',*(['on'] if on else []));col=self.box(True,6);col.set_halign(Gtk.Align.CENTER)
            col.add(self.badge(icon,40,self.p['accent'] if on else self.p['accent_soft'],self.p['on_accent'] if on else self.p['accent_text']))
            l=Gtk.Label(label=text);l.set_justify(Gtk.Justification.CENTER);l.set_line_wrap(True);l.set_max_width_chars(14);col.add(l)
            if a in NEW:tag=self.cls(Gtk.Label(label=self.t('YENİ','NÛ')),'new-tag');tag.set_halign(Gtk.Align.CENTER);col.add(tag)
            b.add(col);b.set_sensitive(not self.busy);b.connect('clicked',lambda _b,a=a:self.pick_tool(a));grid.attach(b,n%4,n//4,1,1);n+=1
        if not self.action:
            box=self.box();box.add(grid);box.add(self.label(self.t('Bir araç seç; ayarları burada açılır.','Amûrekê hilbijêre; mîheng li vir vedibin.'),'small'));return box
        return grid
    def pick_tool(self,a):
        if self.busy:return
        self.action=a;self.summary=None;self.clear_preview(rebuild=False);self.build()
    def options_card(self):
        c=self.card(10);a=self.action;info=self.source;text,icon=self.action_label(a)
        head=self.box(False,12);head.add(self.badge(icon,36));head.add(self.label(text,'head',False));c.add(head)
        desc=lambda s:c.add(self.label(s,'muted'))
        if a=='watermark':
            if info.kind=='pdf':
                desc(self.t('Önce otomatik bulunur: filigran katmanları, açıklamalar ve yarı saydam eğik yazılar. Yazı bilinirse ondan geçen her yazı bloğu silinir. İşe yaramazsa soldaki sayfada alanı çerçevele; o alan çevresinin rengiyle kapatılır.','Pêşî bixweber tê dîtin: qatên nîşana avê, şîrove û nivîsên nîv-zelal û xwar. Ger nivîs were zanîn, her bloka wê tê jêbirin. Ger nebe, qadê çarçove bike.'))
                c.add(self.label(self.t('Ne aransın?','Çi bê lêgerîn?'),'caption'));c.add(self.toggles(['auto','repeated'],[self.t('Otomatik bul','Bixweber bibîne'),self.t('Her sayfada tekrar eden logo/görseller','Logo/wêneyên dubare')],['1','0']))
                self.field('keyword',self.t('Filigrandaki yazı (isteğe bağlı)','Nivîsa nîşana avê (ne mecbûrî)'),'',self.t('ör. GİZLİ, TASLAK, site adı','mînak: NIHÊNÎ'),c)
            else:
                desc(self.t('Logo, yazı veya filigran kaldırılır. Soldaki görüntüde alanı fareyle çerçevele. Doldur: çevredeki görüntüden tamamlar. Bulanıklaştır: alanı okunmaz hâle getirir.','Logo, nivîs an nîşana avê tê rakirin. Li çepê qadê çarçove bike. Tije bike: ji derdorê temam dike. Şêlû bike: qadê nexwendî dike.'))
                c.add(self.label(self.t('Yöntem','Rêbaz'),'caption'));c.add(self.choice('mode',['fill','blur'],[self.t('Doldur (çevreden tamamla)','Tije bike'),self.t('Bulanıklaştır','Şêlû bike')],'fill'))
            self.region_note=self.label(self.region_text(),'small');c.add(self.region_note)
        elif a=='denoise':
            desc(self.t('Hışırtı, cızırtı, tıkırtı ve elektrik uğultusu azaltılır; video görüntüsüne dokunulmaz. Önizle ile 10 saniyelik parçayı önce/sonra dinleyebilirsin.','Xişxiş, çirçir, tiqtiq û gimgima elektrîkê kêm dibin; wêneyê vîdyoyê nayê guhertin.'))
            c.add(self.label(self.t('Temizleme gücü','Hêza paqijkirinê'),'caption'));c.add(self.choice('level',['1','2','3'],[self.t('Hafif','Sivik'),self.t('Orta','Navîn'),self.t('Güçlü','Xurt')],'2'))
            c.add(self.label(self.t('Neler temizlensin?','Çi bê paqijkirin?'),'caption'))
            c.add(self.toggles(['hiss','clicks','hum','voice','loud'],[self.t('Hışırtı / arka plan gürültüsü','Xişxiş / dengê paşxanê'),self.t('Cızırtı ve tıkırtı','Çirçir û tiqtiq'),self.t('Uğultu (elektrik)','Gimgim (elektrîk)'),self.t('Konuşmayı netleştir','Axaftinê zelal bike'),self.t('Ses seviyesini dengele','Asta dengê hevseng bike')],['1','1','1','0','1']))
            self.field('at',self.t('Önizleme başlangıcı','Destpêka pêşdîtinê'),'0','0:00',c)
        elif a=='compress':
            if info.kind=='pdf':desc(self.t('PDF\'deki büyük resimler yeniden sıkıştırılır; yazılar yazı olarak kalır.','Wêneyên mezin ji nû ve têne pêçandin; nivîs wek nivîs dimînin.'))
            else:desc(self.t('Dosya boyutu küçülür. Önizle ile birkaç saniyelik örneği görüp tahmini boyutu öğrenebilirsin.','Mezinahiya dosyeyê kêm dibe. Bi Pêşdîtinê mezinahiya texmînî bibîne.'))
            c.add(self.label(self.t('Sıkıştırma','Pêçandin'),'caption'));c.add(self.choice('level',['1','2','3'],[self.t('Hafif','Sivik'),self.t('Dengeli','Hevseng'),self.t('Güçlü','Xurt')],'2'))
            if info.kind=='video':c.add(self.label(self.t('Çözünürlük','Çareserî'),'caption'));c.add(self.choice('height',['0','1080','720','480'],[self.t('Aynı','Wek xwe'),'1080p','720p','480p'],'0'))
        elif a=='pages':
            desc(self.t('Seçtiğin sayfaları yeni PDF\'de tut ya da sil. Sırayı değiştirmek için 3,1,2 yaz.','Rûpelên hilbijartî bihêle an jê bibe. Ji bo rêzê 3,1,2 binivîse.'))
            c.add(self.choice('keep',['1','0'],[self.t('Seçilenleri tut','Hilbijartiyan bihêle'),self.t('Seçilenleri sil','Hilbijartiyan jê bibe')],'1'))
            self.field('spec',self.t('Sayfalar','Rûpel')+(f' (1–{self.pdf_count})' if self.pdf_count else ''),'1',self.t('ör. 1-3, 5, 8-','mînak: 1-3, 5, 8-'),c)
        elif a=='pdf_rotate':
            c.add(self.label(self.t('Açı','Goşe'),'caption'));c.add(self.choice('angle',['90','180','270'],['90° ↻','180°','90° ↺'],'90'))
            self.field('spec',self.t('Sayfalar · boşsa hepsi','Rûpel · vala be hemû'),'',self.t('hepsi','hemû'),c)
        elif a=='edit':
            desc(self.t('Döndür, aynala, küçült veya siyah-beyaz yap. Biçim korunur.','Bizivirîne, berevajî bike, biçûk bike an reş û spî bike.'))
            c.add(self.label(self.t('Döndür','Bizivirîne'),'caption'));c.add(self.choice('angle',['0','90','180','270'],['0°','90° ↻','180°','90° ↺'],'0'))
            c.add(self.label(self.t('Boyut','Mezinahî'),'caption'));c.add(self.choice('scale',['100','75','50','25'],['%100','%75','%50','%25'],'100'))
            c.add(self.toggles(['flip','gray'],[self.t('Aynala','Berevajî bike'),self.t('Siyah-beyaz','Reş û spî')],['0','0']))
        elif a=='images_pdf':
            desc(self.t('Fotoğraflar sırayla tek PDF\'de birleşir. Listedeki bütün fotoğraflar için aşağıdaki kutuyu işaretle ya da ikinci bir fotoğraf seç.','Wêne di PDFekê de yek dibin.'));c.add(self.other_picker())
        elif a=='ocr_image':
            desc(self.t('Fotoğraftaki yazı okunur. OCR hataları olabilir.','Nivîsa wêneyê tê xwendin.'))
            c.add(self.label(self.t('Çıktı biçimi','Formata encamê'),'caption'));c.add(self.choice('format',['txt','pdf','docx','odt'],['TXT','PDF','DOCX','ODT'],'txt'))
            c.add(self.label(self.t('Yazının dili','Zimanê nivîsê'),'caption'));c.add(self.choice('lang',['tur+eng','tur','eng','kmr','ara','fas'],['Türkçe + English','Türkçe','English','Kurmancî','العربية','فارسی'],'tur+eng'))
        elif a=='transcribe':
            desc(self.t('TXT düz metin veya SRT altyazı. Müzik ve gürültü tanımayı etkileyebilir.','TXT nivîsa sade an SRT binivîs.'))
            c.add(self.choice('speech_format',['txt','srt'],['TXT','SRT'],'txt'));c.add(self.label(self.t('Konuşmanın dili','Zimanê axaftinê'),'caption'));c.add(self.choice('speech_language',['tr','en'],['Türkçe','English'],'tr'));self.times(c)
        elif a=='add_subtitle':
            desc(self.t('SRT, ASS veya VTT altyazıyı videoya ekler. Kalıcı: görüntüye yazılır. Açılıp kapatılabilir: ayrı iz.','Binnivîsê li vîdyoyê zêde dike.'));c.add(self.other_picker(self.t('Altyazı dosyasını seç','Pela binnivîsê hilbijêre')))
            c.add(self.choice('subtitle_mode',['burn','soft'],[self.t('Kalıcı','Mayînde'),self.t('Açılıp kapatılabilir','Vekirin/girtin dibe')],'burn'))
        elif a in ('subtitle_text','subtitle_restore'):
            desc(self.t('Çeviri ayrı programda yapılır. Her altyazıyı tek satırda tut; satır sayısını ve sırasını koru.','Di bernameyeke din de wergerîne; hejmar û rêza rêzan biparêze.'))
            if a=='subtitle_restore':c.add(self.other_picker(self.t('Orijinal SRT dosyasını seç','SRT ya orîjînal hilbijêre')))
        elif a=='split' and info.kind not in ('video','audio'):self.field('page_count',self.t('Her dosyada kaç sayfa olsun?','Di her dosyeyê de çend rûpel?'),'1','1',c)
        elif a=='merge':desc(self.t('Seçili dosyanın arkasına ikinci dosya eklenir. Hepsini birleştirmek için aşağıdaki kutuyu işaretle.','Dosyeya duyem li pey tê zêdekirin.'));c.add(self.other_picker())
        elif a in ('add_audio','replace_audio'):
            c.add(self.other_picker(self.t('Eklenecek ses dosyasını seç','Dosyeya deng hilbijêre')));desc(self.t('Sesin videoda başlayacağı ve biteceği zaman:','Dema destpêk û dawiya deng:'));self.times(c)
            row=self.box(False,12);x=self.box();y=self.box();self.field('audio_start',self.t('Ses dosyasında başlangıç','Destpêka deng'),'0','0:00',x);self.field('audio_end',self.t('Ses dosyasında bitiş','Dawiya deng'),'',self.t('sona kadar','heta dawiyê'),y);row.pack_start(x,True,True,0);row.pack_start(y,True,True,0);c.add(row)
        elif a=='mute':desc(self.t('Videonun bütün sesi kaldırılır.','Hemû deng tê rakirin.'))
        elif info.kind in ('video','audio'):
            desc({'trim':self.t('Başlangıç ve bitiş arası ayrı bir dosyaya kaydedilir.','Navbera destpêk û dawiyê tê tomarkirin.'),'remove_range':self.t('Seçtiğin bölüm silinir, kalanlar birleştirilir.','Beşa hilbijartî tê rakirin.')}.get(a,self.t('İşlemin uygulanacağı zaman aralığı:','Navbera demê:')))
            self.times(c,a!='frame')
            if a=='split':self.field('part',self.t('Her parça kaç saniye olsun?','Her parçe çend çirke?'),'60','60',c)
            if a=='rotate':c.add(self.label(self.t('Açı','Goşe'),'caption'));c.add(self.choice('factor',['90','180','270'],['90° ↻','180°','90° ↺'],'90'))
            if a=='speed':c.add(self.label(self.t('Hız','Lez'),'caption'));c.add(self.choice('factor',['0.5','0.75','1.25','1.5','2'],['0.5×','0.75×','1.25×','1.5×','2×'],'1.5'))
            if a=='volume':c.add(self.label(self.t('Ses düzeyi','Asta dengê'),'caption'));c.add(self.choice('factor',['0.25','0.5','0.75','1.5','2','3'],['%25','%50','%75','%150','%200','%300'],'1.5'))
        return c
    def other_picker(self,title=None):
        col=self.box(True,6);col.add(self.button((self.t('Değiştir: ','Biguherîne: ')+self.other.path.name) if self.other else (title or self.t('Arkasına eklenecek dosyayı seç','Dosyeya duyem hilbijêre')),'folder','soft',self.pick_other,not self.busy))
        return col

    # ------------------------------------------------------------- status / result
    def set_status(self,text):
        self.status=text
        if self.status_label is not None:self.status_label.set_text(text)
        return False
    def status_box(self,into,always):
        if not always and not self.busy and not self.notice:return
        c=self.box(True,8);self.status_label=self.label(self.notice if (not always and self.notice) else (self.status or self.t('Hazır.','Amade ye.')));c.add(self.status_label)
        if self.busy:
            self.progress_bar=Gtk.ProgressBar();self.progress_bar.set_show_text(self.progress_value is not None)
            if self.progress_value is not None:self.progress_bar.set_fraction(self.progress_value)
            else:self.progress_bar.pulse()
            c.add(self.progress_bar);c.add(self.button(self.t('Durdur','Rawestîne'),'stop','danger',self.cancel))
        into.add(c)
    def result_card(self):
        c=self.card(10);row=self.box(False,12);row.add(self.badge('check',40,self.p['success_soft'],self.p['success']));row.add(self.label(self.summary,'section',False));c.add(row)
        if self.last_outputs:
            r=self.box(False,10);r.pack_start(self.button(self.t('Aç','Veke'),'open','soft',lambda:self.launch(self.last_outputs[0])),True,True,0)
            r.pack_start(self.button(self.t('Klasörde göster','Di peldankê de nîşan bide'),'folder','soft',lambda:self.reveal(self.last_outputs[0])),True,True,0);c.add(r)
        return c
    def launch(self,path):
        try:Gio.AppInfo.launch_default_for_uri(Path(path).as_uri(),None)
        except Exception as e:self.fail(e)
    def reveal(self,path):
        try:
            bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
            bus.call_sync('org.freedesktop.FileManager1','/org/freedesktop/FileManager1','org.freedesktop.FileManager1','ShowItems',GLib.Variant('(ass)',([Path(path).as_uri()],'')),None,Gio.DBusCallFlags.NONE,3000,None)
        except Exception:self.launch(Path(path).parent)
    def error_text(self,e):
        key=str(e) if isinstance(e,OperationError) else getattr(e,'code',None)
        if key in ERRORS:return ERRORS[key][1 if self.ku else 0]
        lang='ku' if self.ku else 'tr'
        try:
            from .extras import TEXT
            if key in TEXT[lang]:return TEXT[lang][key]
        except Exception:pass
        if key and key in STRINGS[lang]:
            detail=getattr(e,'detail','')
            return STRINGS[lang][key]+((': '+detail) if key in {'missing_tool','unsupported','not_file'} and detail else '')
        return str(e)[:400]
    def fail(self,e):
        text=self.t('İşlem tamamlanamadı: ','Kar nehat temamkirin: ')+self.error_text(e);self.log.append(text)
        if getattr(e,'detail','') and len(str(e.detail))>0:self.log.append(str(e.detail)[-2000:])
        self.set_status(text)
        if self.status_label is None:
            d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.CLOSE,text=text);d.run();d.destroy()
        return False

    # ------------------------------------------------------------- running
    def options(self):
        opts={k.split('.',1)[1]:v for k,v in self.vals.items() if k.startswith(self.action+'.')}
        opts['quality']=self.quality
        if self.action=='watermark':
            opts['regions']=so.region_text(self.regions)
            if self.source.kind!='pdf' and not self.regions:raise OperationError('watermark_area')
        return opts
    def start(self):
        if self.busy or self.source is None:return
        try:opts=self.options();jobs.check(self.source,self.action,opts,self.other,self.batch and len(self.files)>1)
        except Exception as e:self.fail(e);return
        targets=[f['info'] for f in self.files] if self.batch and len(self.files)>1 else [self.source]
        action=self.action;target=self.target;other=self.other;source=self.source
        conv=core.Options(self.quality,self.resolution,'auto',self.only_text,self.ocr,self.ocr_lang)
        self.begin(self.t('İşlem başladı…','Kar dest pê kir…'))
        def work():
            try:
                outputs,failed=jobs.run(self.runner,targets,source,action,target,opts,conv,other,self.output,self.ku,self.log.append,self.error_text,self.set_status_bg)
                GLib.idle_add(self.finished,outputs,failed,False,action)
            except core.Cancelled:GLib.idle_add(self.finished,[],0,True,action)
            except Exception as e:self.log.append(traceback.format_exc()[-2000:]);GLib.idle_add(self.finished,[],1,False,action,e)
        threading.Thread(target=work,daemon=True).start()
    def begin(self,text):
        self.busy=True;self.summary=None;self.last_outputs=[];self.progress_value=None;self.status=text
        self.runner=core.Runner(progress=lambda v:GLib.idle_add(self.set_progress,v));self.build()
        self.pulse_id=GLib.timeout_add(150,self.pulse)
    def set_progress(self,v):
        self.progress_value=max(0.0,min(1.0,float(v)))
        for bar in (self.progress_bar,getattr(self,'side_progress',None)):
            if bar is not None:bar.set_show_text(True);bar.set_fraction(self.progress_value)
        return False
    def pulse(self):
        if not self.busy:return False
        if self.progress_value is None:
            for bar in (self.progress_bar,getattr(self,'side_progress',None)):
                if bar is not None:bar.pulse()
        return True
    def cancel(self):
        if self.runner:self.runner.cancel()
        self.set_status(self.t('Durduruluyor…','Tê rawestandin…'))
    def finished(self,outputs,failed,cancelled,action,error=None):
        self.busy=False;self.runner=None;self.progress_value=None;self.last_outputs=[Path(o) for o in outputs]
        for o in self.last_outputs:self.remember(o,action)
        if cancelled:self.status=self.t('İşlem durduruldu. Tamamlanan çıktılar ve orijinaller korunuyor.','Kar hat rawestandin. Encamên qediyayî û yên resen tên parastin.')
        elif error is not None:self.status=self.t('İşlem tamamlanamadı: ','Kar nehat temamkirin: ')+self.error_text(error)
        else:self.status=self.t('İşlem bitti.','Kar qediya.') if outputs else self.t('İşlem tamamlanamadı. Ayrıntılar aşağıda.','Kar nehat temamkirin. Hûrgilî li jêr.')
        if outputs or failed:self.summary=self.t('Kaydedilen: ','Tomarkirî: ')+str(len(outputs))+(self.t(' · Hatalı: ',' · Çewt: ')+str(failed) if failed else '')
        if failed and not outputs:self.show_log=True
        self.drop_cache();self.build();self.notify(self.summary or self.status)
        return False
    def notify(self,text):
        app=self.get_application()
        if not app or self.is_active():return
        try:
            n=Gio.Notification.new(self.t('Dönüştürücü','Veguherîner'));n.set_body(text);n.set_icon(Gio.ThemedIcon.new('donusturucu'));app.send_notification('finished',n)
        except Exception:pass

    # ------------------------------------------------------------- preview
    def previewable(self):
        a=self.action
        if a in ('transcribe','subtitle_text','subtitle_restore',''):return False
        if a in ('add_audio','replace_audio','add_subtitle','merge','images_pdf') and self.other is None:return False
        return True
    def clear_preview(self,rebuild=True):
        if self.preview_view is not None:
            for pl in list(ui.Player.live):
                if pl.is_ancestor(self.preview_view):pl.stop()
        self.preview=None;self.preview_view=None
    def run_preview(self):
        if self.busy:return
        try:opts=self.options();jobs.check(self.source,self.action,opts,self.other,True)
        except Exception as e:self.fail(e);return
        info=self.source;action=self.action;target=self.target;conv=core.Options(self.quality,self.resolution,'auto',self.only_text,self.ocr,self.ocr_lang)
        page=self.pdf_page;other=self.other
        self.begin(self.t('Önizleme hazırlanıyor…','Pêşdîtin tê amadekirin…'))
        def work():
            folder=Path(tempfile.mkdtemp(prefix='donustur-preview-'))
            try:GLib.idle_add(self.preview_ready,jobs.preview(self.runner,info,action,target,opts,conv,other,page,folder,self.ku,self.set_status_bg),None)
            except core.Cancelled:GLib.idle_add(self.preview_ready,None,None)
            except Exception as e:self.log.append(traceback.format_exc()[-1500:]);GLib.idle_add(self.preview_ready,None,e)
        threading.Thread(target=work,daemon=True).start()
    def preview_ready(self,p,error):
        self.busy=False;self.runner=None;self.progress_value=None
        if p:
            try:
                for key in ('before','after'):
                    if p.get(key) is not None:p[key]=self.pb(p[key])
                if p.get('thumbs'):p['thumbs']=[(self.pb(path,700),cap) for path,cap in p['thumbs']]
                if p['kind']=='compare' and p.get('before') is None:p['before']=self.base
                p['show']=1;self.preview=p;self.status=self.t('Önizleme hazır. Beğendiysen Başlat\'a bas.','Pêşdîtin amade ye. Ger baş be, Dest pê bike.')
            except Exception as e:error=e;p=None
        if not p:self.status=self.t('Önizleme hazırlanamadı: ','Pêşdîtin nehat amadekirin: ')+self.error_text(error) if error is not None else self.t('Önizleme durduruldu.','Pêşdîtin hat rawestandin.')
        self.preview_view=None;self.build();return False
    def pb(self,path,side=1400):return GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),side,side,True)
    def preview_side(self,i):
        if self.preview:
            for pl in list(ui.Player.live):
                if self.preview_view is not None and pl.is_ancestor(self.preview_view):pl.stop()
            self.preview['show']=i;self.preview_view=None;self.build()
    def set_status_bg(self,text):GLib.idle_add(self.set_status,text)
    def preview_card(self):
        p=self.preview;c=self.card(10);head=self.box(False);head.pack_start(self.label(self.t('Önizleme','Pêşdîtin'),'head'),True,True,0)
        head.add(self.icon_button('close',lambda:(self.clear_preview(),self.build())));c.add(head);k=p['kind']
        if k=='compare':
            c.add(ui.Picture(self.p,p['before'],ui.Picture.COMPARE,after=p['after'],labels=(self.t('Önce','Berê'),self.t('Sonra','Paşê')),height=460))
            c.add(self.label(self.t('Çizgiyi sürükleyerek karşılaştır.','Xetê bikişîne û berhev bike.'),'small'))
        elif k=='image':c.add(ui.Picture(self.p,p['after'],height=460))
        elif k=='audio':
            for title,peaks,path in [(self.t('Orijinal','Resen'),p.get('peaks_a'),p.get('original')),(self.t('Sonuç','Encam'),p.get('peaks_b'),p.get('result'))]:
                c.add(self.label(title,'caption'));c.add(ui.Player(self.p,path,so.detect(path).duration,peaks=peaks or []))
        elif k=='thumbs':
            flow=Gtk.FlowBox();flow.set_selection_mode(Gtk.SelectionMode.NONE);flow.set_max_children_per_line(4);flow.set_column_spacing(10);flow.set_row_spacing(10)
            for pb,cap in p['thumbs']:
                col=self.box(True,4);s=min(1.0,150/pb.get_height());img=Gtk.Image.new_from_pixbuf(pb.scale_simple(max(1,int(pb.get_width()*s)),max(1,int(pb.get_height()*s)),GdkPixbuf.InterpType.BILINEAR));col.add(img);col.add(self.label(cap,'small',False));flow.add(col)
            c.add(flow)
        elif k=='text':t=self.label(p.get('text') or '—','mono');t.set_selectable(True);c.add(t)
        if p.get('result') and k in ('compare','image') and str(p['result']).endswith(('.mp4','.mkv','.webm','.mov','.avi','.mpeg','.ts')):
            # The short sample before and after, played right here.
            show=p.get('show',1)
            c.add(self.segmented([self.t('Orijinal','Resen'),self.t('Sonuç','Encam')],show if p.get('original') else 1,self.preview_side))
            path=p['result'] if show or not p.get('original') else p['original']
            try:info=so.detect(path);c.add(ui.Player(self.p,path,info.duration,size=so.shown_size(info)))
            except Exception:pass
        if p.get('note'):c.add(self.label(p['note'].strip()))
        return c

    # ------------------------------------------------------------- history and settings
    def history_path(self):return runtime.config_dir()/'history.json'
    def history(self):
        try:return json.loads(self.history_path().read_text(encoding='utf-8'))
        except Exception:return []
    def remember(self,path,action):
        h=[{'path':str(path),'action':action,'time':time.time()}]+[x for x in self.history() if x.get('path')!=str(path)]
        try:self.history_path().parent.mkdir(parents=True,exist_ok=True);self.history_path().write_text(json.dumps(h[:80],ensure_ascii=False),encoding='utf-8')
        except OSError:pass
    def history_row(self,h):
        path=Path(h['path']);ev=Gtk.EventBox();row=self.cls(self.box(False,12),'row-card');ev.add(row);ev.connect('button-release-event',lambda *_:self.launch(path))
        ext=path.suffix.lower()[1:];icon='video' if ext in core.VIDEO and ext!='gif' else 'audio' if ext in core.AUDIO else 'image' if ext in ('png','jpg','webp','bmp','gif') else 'doc'
        row.add(self.badge(icon,44));col=self.box(True,2);n=Gtk.Label(label=path.name);n.set_xalign(0);n.set_ellipsize(Pango.EllipsizeMode.MIDDLE);self.cls(n,'section');col.add(n)
        tr,ku,_=L.get(h.get('action'),(h.get('action',''),h.get('action',''),''));when=time.strftime('%d.%m.%Y %H:%M',time.localtime(h.get('time',0)))
        col.add(self.label((ku if self.ku else tr)+' · '+when+('' if path.exists() else self.t(' · taşınmış veya silinmiş',' · hatiye guhestin an jêbirin')),'small',False));row.pack_start(col,True,True,0)
        row.add(self.icon_button('folder',lambda:self.reveal(path),self.t('Klasörde göster','Di peldankê de nîşan bide')));return ev
    def build_history(self):
        self.page.add(self.label(self.t('Geçmiş','Dîrok'),'title'));h=self.history()
        if not h:self.page.add(self.label(self.t('Henüz dönüştürme yok. Dönüştürdüğün dosyalar burada listelenir; tıklayınca açılır.','Hîn veguherîn tune.'),'muted'));return
        head=self.box(False);head.pack_start(self.label(f'{len(h)} '+self.t('dosya','dosye'),'small'),True,True,0)
        head.add(self.button(self.t('Geçmişi temizle','Dîrokê paqij bike'),None,'plain',lambda:(self.history_path().unlink(missing_ok=True),self.build())));self.page.add(head)
        for x in h:self.page.add(self.history_row(x))
        self.page.add(self.label(self.t('Geçmişten silmek dosyayı silmez.','Jêbirina ji dîrokê dosyeyê jê nabe.'),'small'))
    def build_settings(self):
        self.page.add(self.label(self.t('Ayarlar','Mîheng'),'title'))
        grid=self.box(True,14);grid.set_size_request(-1,-1)
        def head(icon,text):r=self.box(False,10);r.add(self.badge(icon,32));r.add(self.label(text,'section',False));return r
        c=self.card();c.add(head('translate',self.t('Dil','Ziman')));c.add(self.chips(['Türkçe','Kurmancî'],1 if self.ku else 0,lambda i:(setattr(self,'ku',i==1),self.save(),self.build())));grid.add(c)
        c=self.card();c.add(head('palette',self.t('Görünüm','Xuyang')));modes=list(theme.MODES)
        c.add(self.chips([self.t('Sistem','Pergal'),self.t('Aydınlık','Ronî'),self.t('Karanlık','Tarî')],modes.index(self.theme_mode),lambda i:(setattr(self,'theme_mode',modes[i]),self.save(),self.relook())))
        c.add(self.label(self.t('Vurgu rengi','Rengê sereke'),'caption'));sw=self.box(False,10)
        for i in range(len(ui.ACCENTS)):
            b=Gtk.Button();self.cls(b,'swatch',f'swatch-{i}',*(['on'] if i==self.accent else []));b.set_size_request(36,36)
            if i==self.accent:b.add(ui.icon('check','#ffffff',18))
            b.connect('clicked',lambda _b,i=i:(setattr(self,'accent',i),self.save(),self.relook()));sw.add(b)
        c.add(sw);grid.add(c)
        c=self.card();c.add(head('folder',self.t('Kayıt klasörü','Peldanka tomarkirinê')));c.add(self.label(str(self.output),'muted'))
        r=self.box(False,10);r.add(self.button(self.t('Değiştir','Biguherîne'),'folder','soft',self.choose_output));r.add(self.button(self.t('Klasörü aç','Peldankê veke'),'open','plain',lambda:self.launch(self.output)));c.add(r);grid.add(c)
        c=self.card();c.add(head('lock',self.t('Gizlilik ve sürüm','Nepenî û guherto')))
        c.add(self.label(self.t('Çevrimdışı çalışır. Dosyalar hiçbir yere yüklenmez; orijinaller değiştirilmez.','Bê înternetê dixebite. Dosye li tu derê nayên barkirin; yên resen nayên guhertin.'),'muted'))
        c.add(self.label('Linux '+VERSION,'small'));grid.add(c)
        c=self.card();c.add(head('build',self.t('Yerel araçlar','Amûrên herêmî')))
        for name,ok in core.tools().items():c.add(self.label(('✓ ' if ok else '✗ ')+name+' — '+(self.t('hazır','amade') if ok else self.t('bulunamadı','nehat dîtin')),'small',False))
        grid.add(c);self.page.add(grid)
    def choose_output(self):
        d=Gtk.FileChooserNative.new(self.t('Kayıt klasörü','Peldanka tomarkirinê'),self,Gtk.FileChooserAction.SELECT_FOLDER,None,None)
        if d.run()==Gtk.ResponseType.ACCEPT:self.output=Path(d.get_filename());self.save();self.build()
    def on_close(self,*_):
        if self.busy and self.runner:
            d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.YES_NO,text=self.t('İşlemi durdurup çıkılsın mı?','Kar were rawestandin û derkeve?'))
            r=d.run();d.destroy()
            if r!=Gtk.ResponseType.YES:return True
            self.runner.cancel()
        self.save();return False

class App(Gtk.Application):
    def __init__(self,paths):
        super().__init__(application_id='org.local.Donusturucu',flags=Gio.ApplicationFlags.NON_UNIQUE);self.paths=paths
    def do_activate(self):
        win=self.get_active_window()
        if win:win.present()
        else:Window(self,self.paths)

def main():
    import sys
    paths=[str(Path(p).expanduser().resolve()) for p in sys.argv[1:] if not p.startswith('--')]
    return App(paths).run([sys.argv[0]])

if __name__=='__main__':main()
