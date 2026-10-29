"""GTK bağımlılığı olmayan Windows/macOS/Linux arayüzü (Python/Tk)."""
from pathlib import Path
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from . import core,runtime,theme,tktheme,VERSION
from .i18n import STRINGS

class Window(tk.Tk):
    def __init__(self,paths=()):
        super().__init__()
        self.geometry('1160x880');self.minsize(940,800)
        self.config_file=runtime.config_dir()/'settings.json'
        try:config=json.loads(self.config_file.read_text(encoding='utf-8'))
        except (OSError,ValueError):config={}
        self.lang=config.get('language','tr')
        if self.lang not in STRINGS:self.lang='tr'
        self.output=Path(config.get('output',str(Path.home()/'Dönüştürülenler')))
        self.items={};self.bindings=[];self.events=queue.Queue();self.running=False;self.detecting=False;self.stopping=False;self.runner=None;self.current=None;self.logs=[]
        self.style=ttk.Style(self);self.style.theme_use('clam');self.font=tktheme.pick_font(self)
        self.theme_mode=config.get('theme','system') if config.get('theme') in theme.MODES else 'system';self.active_theme=None;self.text_widgets=[]
        self.apply_theme()
        self.build();self.translate();self.protocol('WM_DELETE_WINDOW',self.close)
        self.after(80,self.drain);self.after(2000,self.watch_theme)
        if paths:self.after(150,lambda:self.add_paths(paths))
    def t(self,k):return STRINGS[self.lang].get(k,k)
    def apply_theme(self):
        name=theme.resolve(self.theme_mode)
        if name==self.active_theme:return
        self.active_theme=name;tktheme.apply(self,name,self.font);p=theme.PALETTES[name]
        for widget in self.text_widgets:widget.configure(bg=p['surface'],fg=p['text'],insertbackground=p['text'],selectbackground=p['selection'],selectforeground=p['selection_fg'],relief='flat',highlightthickness=0,font=(self.font,10))
        if hasattr(self,'tree'):
            for state,color in [('done','success'),('failed','danger'),('cancelled','warning'),('running','info')]:self.tree.tag_configure(state,foreground=p[color])
        self.save()
    def watch_theme(self):
        if self.theme_mode=='system':self.apply_theme()
        self.after(2000,self.watch_theme)
    def change_theme(self,event=None):
        names={self.t('theme_'+m):m for m in theme.MODES};self.theme_mode=names.get(self.theme_box.get(),'system');self.apply_theme();self.save()
    def label(self,parent,key,style='Card.TLabel',**kwargs):
        w=ttk.Label(parent,style=style,**kwargs);self.bindings.append((w,key));return w
    def button(self,parent,key,callback,style='TButton'):
        w=ttk.Button(parent,command=callback,style=style);self.bindings.append((w,key));return w
    def build(self):
        outer=ttk.Frame(self,padding=22);outer.pack(fill='both',expand=True)
        top=ttk.Frame(outer);top.pack(fill='x')
        self.label(top,'title','MainTitle.TLabel').pack(side='left')
        self.language=ttk.Combobox(top,values=['Türkçe','Kurmancî'],state='readonly',width=13)
        self.language.set('Kurmancî' if self.lang=='ku' else 'Türkçe');self.language.pack(side='right')
        self.language.bind('<<ComboboxSelected>>',self.change_language)
        self.theme_box=ttk.Combobox(top,state='readonly',width=12);self.theme_box.pack(side='right',padx=(0,8))
        self.theme_box.bind('<<ComboboxSelected>>',self.change_theme)
        self.button(top,'dependencies',self.show_tools).pack(side='right',padx=10)
        self.label(outer,'tagline','Hint.TLabel').pack(anchor='w',pady=(4,12))
        addrow=ttk.Frame(outer,padding=14,style='Card.TFrame');addrow.pack(fill='x')
        drop=ttk.Frame(addrow,style='CardInner.TFrame');drop.pack(side='left',fill='x',expand=True)
        self.label(drop,'drop','Section.TLabel').pack(anchor='w');self.label(drop,'offline','Badge.TLabel').pack(anchor='w',pady=(6,0))
        self.add_btn=self.button(addrow,'add',self.choose_files,'Start.TButton');self.add_btn.pack(side='right')
        self.folder_add_btn=self.button(addrow,'add_folder',self.choose_folder);self.folder_add_btn.pack(side='right',padx=6)
        body=ttk.Frame(outer);body.pack(fill='both',expand=True,pady=12)
        left=ttk.Frame(body,style='Card.TFrame',padding=14);left.pack(side='left',fill='both',expand=True)
        self.label(left,'queue','Section.TLabel').pack(anchor='w')
        self.label(left,'batch_note','CardHint.TLabel',wraplength=600).pack(anchor='w',pady=(7,12))
        treebox=ttk.Frame(left,style='CardInner.TFrame');treebox.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(treebox,columns=('file','type','format','status'),show='headings',selectmode='browse',height=6)
        for key,width in [('file',230),('type',155),('format',80),('status',120)]:self.tree.column(key,width=width,minwidth=60,stretch=True)
        scroll=ttk.Scrollbar(treebox,command=self.tree.yview);scroll.pack(side='right',fill='y')
        self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.select)
        row=ttk.Frame(left,style='CardInner.TFrame');row.pack(fill='x',pady=(10,0))
        self.remove_btn=self.button(row,'remove',self.remove);self.remove_btn.pack(side='left')
        self.clear_btn=self.button(row,'clear',self.clear);self.clear_btn.pack(side='left',padx=8)
        self.extras_btn=self.button(row,'extras',self.open_extras);self.extras_btn.pack(side='right')
        right=ttk.Frame(body,style='Card.TFrame',padding=16,width=340);right.pack(side='right',fill='y',padx=(14,0));right.pack_propagate(False)
        self.label(right,'settings','Section.TLabel').pack(anchor='w')
        self.empty=self.label(right,'select','CardHint.TLabel',wraplength=300);self.empty.pack(anchor='w',pady=12)
        self.options=ttk.Frame(right,style='CardInner.TFrame')
        self.label(self.options,'target').pack(anchor='w',pady=(15,5))
        self.target=ttk.Combobox(self.options,state='readonly',height=18);self.target.pack(fill='x')
        self.target.bind('<<ComboboxSelected>>',self.update_options)
        self.count=ttk.Label(self.options,style='CardHint.TLabel');self.count.pack(anchor='w',pady=(4,8))
        self.video_options=ttk.Frame(self.options,style='CardInner.TFrame')
        self.label(self.video_options,'quality').pack(anchor='w',pady=(5,4))
        self.quality=ttk.Combobox(self.video_options,state='readonly');self.quality.pack(fill='x');self.quality.bind('<<ComboboxSelected>>',self.update_options)
        self.label(self.video_options,'resolution').pack(anchor='w',pady=(8,4))
        self.resolution=ttk.Combobox(self.video_options,state='readonly');self.resolution.pack(fill='x');self.resolution.bind('<<ComboboxSelected>>',self.update_options)
        self.audio_options=ttk.Frame(self.options,style='CardInner.TFrame')
        self.text_options=ttk.Frame(self.options,style='CardInner.TFrame')
        self.only_text=tk.BooleanVar();self.use_ocr=tk.BooleanVar()
        only=ttk.Checkbutton(self.text_options,variable=self.only_text,command=self.update_options,style='Card.TCheckbutton');self.bindings.append((only,'only_text'));only.pack(anchor='w',pady=4)
        ocr=ttk.Checkbutton(self.text_options,variable=self.use_ocr,command=self.update_options,style='Card.TCheckbutton');self.bindings.append((ocr,'use_ocr'));ocr.pack(anchor='w',pady=4)
        self.text_checks=[only,ocr]
        self.label(self.text_options,'ocr_language').pack(anchor='w',pady=4)
        self.ocr_names={'Türkçe + English':'tur+eng','Kurmancî + English':'kmr+eng','English':'eng','العربية / Arapça + English':'ara+eng','فارسی / Farsça + English':'fas+eng','العربية + فارسی + English':'ara+fas+eng','Türkçe + Kurmancî + English':'tur+kmr+eng'}
        self.ocr_lang=ttk.Combobox(self.text_options,state='readonly',values=list(self.ocr_names));self.ocr_lang.pack(fill='x');self.ocr_lang.bind('<<ComboboxSelected>>',self.update_options)
        self.apply_all=tk.BooleanVar(value=False);self.apply_all_check=ttk.Checkbutton(self.options,variable=self.apply_all,style='Card.TCheckbutton');self.bindings.append((self.apply_all_check,'apply_all'));self.apply_all_check.pack(anchor='w',pady=5)
        self.note=ttk.Label(self.options,style='CardHint.TLabel',wraplength=300,justify='left');self.note.pack(anchor='w',pady=14)
        folder=ttk.Frame(outer,style='Card.TFrame',padding=14);folder.pack(fill='x')
        self.label(folder,'output','Section.TLabel').pack(anchor='w')
        row=ttk.Frame(folder,style='CardInner.TFrame');row.pack(fill='x',pady=(6,0))
        self.path_label=ttk.Label(row,text=str(self.output),style='Card.TLabel',wraplength=650);self.path_label.pack(side='left',fill='x',expand=True)
        self.folder_btn=self.button(row,'choose',self.choose_output);self.folder_btn.pack(side='right',padx=(8,0))
        self.button(row,'open',self.open_output).pack(side='right')
        self.progress=ttk.Progressbar(outer,mode='determinate',maximum=1);self.progress.pack(fill='x',pady=10)
        footer=ttk.Frame(outer);footer.pack(fill='x')
        self.status=ttk.Label(footer,style='Hint.TLabel',wraplength=430);self.status.pack(side='left',fill='x',expand=True)
        self.button(footer,'details',self.show_log).pack(side='right',padx=(8,0))
        self.stop_btn=self.button(footer,'cancel',self.cancel,'Stop.TButton');self.stop_btn.pack(side='right',padx=(8,0));self.stop_btn.state(['disabled'])
        self.start_btn=self.button(footer,'start',self.start,'Start.TButton');self.start_btn.pack(side='right');self.start_btn.state(['disabled'])
    def translate(self):
        self.title(self.t('title'))
        self.theme_box.configure(values=[self.t('theme_'+m) for m in theme.MODES]);self.theme_box.set(self.t('theme_'+self.theme_mode))
        for w,key in self.bindings:w.configure(text=self.t(key))
        for key in ('file','type','format','status'):self.tree.heading(key,text=self.t(key))
        for ident,item in self.items.items():self.row(ident)
        self.status.configure(text=self.t('busy' if self.running else 'idle'))
        self.select()
    def change_language(self,event=None):
        self.lang='ku' if self.language.get()=='Kurmancî' else 'tr';self.translate();self.save()
    def save(self):
        try:
            try:data=json.loads(self.config_file.read_text(encoding='utf-8'))
            except (OSError,ValueError):data={}
            data.update(language=getattr(self,'lang','tr'),output=str(self.output),theme=self.theme_mode,active_theme=self.active_theme)
            self.config_file.parent.mkdir(parents=True,exist_ok=True)
            self.config_file.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        except OSError:pass
    def row(self,ident):
        item=self.items[ident];info=item['info'];mark={'pending':'•','running':'◐','done':'✓','failed':'✕','cancelled':'■'}.get(item['status'],'•')
        values=(info.path.name,self.t(info.kind)+' · '+info.fmt.upper(),item['target'].upper(),mark+'  '+self.t(item['status']))
        if self.tree.exists(ident):self.tree.item(ident,values=values,tags=(item['status'],))
        else:self.tree.insert('',tk.END,iid=ident,values=values,tags=(item['status'],))
    def choose_files(self):
        paths=filedialog.askopenfilenames(parent=self,title=self.t('add'))
        if paths:self.add_paths(paths)
    def choose_folder(self):
        folder=filedialog.askdirectory(parent=self,title=self.t('add_folder'))
        if folder:self.apply_all.set(True);self.add_paths([folder])
    def add_paths(self,paths):
        if self.running or self.detecting:return
        self.detecting=True;self.controls(False);self.status.configure(text=self.t('detecting'))
        def worker():
            found=[];errors=[]
            for p in core.expand_paths(paths):
                try:found.append(core.detect(p))
                except Exception as e:errors.append(str(p)+'\n'+self.error_text(e))
            self.events.put(('detected',(found,errors)))
        threading.Thread(target=worker,daemon=True).start()
    def detected(self,found,errors):
        for info in found:
            if any(i['info'].path==info.path for i in self.items.values()):continue
            ident=str(max([int(i) for i in self.items] or [0])+1)
            target='mp3' if info.kind=='audio' else 'mp4' if info.kind=='video' else 'txt' if info.kind=='pdf' or info.fmt=='srt' else 'pdf'
            self.items[ident]={'info':info,'target':target,'options':core.Options(),'status':'pending','result':None};self.row(ident)
        self.detecting=False;self.controls(True);self.status.configure(text=self.t('idle'))
        if self.items and not self.tree.selection():self.tree.selection_set(next(iter(self.items)));self.select()
        if errors:self.logs.extend(errors);messagebox.showwarning(self.t('warning'),'\n'.join(errors),parent=self)
    def select(self,event=None):
        selection=self.tree.selection();self.current=selection[0] if selection else None
        if self.current is None:self.options.pack_forget();self.empty.pack(anchor='w',pady=12);return
        self.empty.pack_forget();self.options.pack(fill='x')
        item=self.items[self.current];info=item['info'];formats=core.targets(info)
        self.target.configure(values=[f.upper() for f in formats]);self.target.set(item['target'].upper());self.target.configure(state='disabled' if self.running else 'readonly')
        self.count.configure(text=self.t('format_count').format(count=len(formats)))
        self.quality.configure(values=[self.t('keep_source' if k=='original' else k) for k in ['original','small','balanced','high']]);self.quality.set(self.t('keep_source' if item['options'].quality=='original' else item['options'].quality))
        self.resolution.configure(values=[self.t('original'),'1080p','720p','480p']);self.resolution.set(self.t('original') if item['options'].resolution=='original' else item['options'].resolution+'p')
        self.video_options.pack_forget();self.audio_options.pack_forget();self.text_options.pack_forget();self.note.pack_forget()
        if info.kind=='video' and item['target'] in core.VIDEO:self.video_options.pack(fill='x')
        
        key={'presentation':'slides_hint','spreadsheet':'sheet_hint','pdf':'pdf_hint','ebook':'ebook_hint','audio':'audio_hint','video':'video_hint'}.get(info.kind,'document_hint')
        if info.kind=='presentation' and item['target'] not in core.SLIDES:key='slides_text_hint'
        if info.kind=='spreadsheet' and item['target'] not in core.SHEET:key='sheet_text_hint'
        if core.text_options_apply(info,item['target']):self.text_options.pack(fill='x')
        self.only_text.set(item['options'].only_text);self.use_ocr.set(item['options'].ocr);self.ocr_lang.set(next((name for name,code in self.ocr_names.items() if code==item['options'].ocr_language),'Türkçe + English'));self.ocr_lang.configure(state='readonly' if item['options'].ocr and not self.running else 'disabled')
        for check in self.text_checks:check.state(['disabled' if self.running else '!disabled'])
        hint=self.t('only_text_hint') if item['options'].only_text else self.t(key)
        self.note.configure(text=hint+(('\n\n'+self.t('gif_hint')) if item['target']=='gif' else ''));self.note.pack(anchor='w',pady=14)
        for w in (self.quality,self.resolution):w.configure(state='disabled' if self.running else 'readonly')
    def update_options(self,event=None):
        if self.running or not self.current:return
        item=self.items[self.current];item['target']=self.target.get().lower()
        quality=next((k for k in ['original','small','balanced','high'] if self.t('keep_source' if k=='original' else k)==self.quality.get()),'balanced')
        resolution=self.resolution.get();resolution='original' if resolution==self.t('original') else resolution.removesuffix('p')
        item['options']=core.Options(quality,resolution,'auto',self.only_text.get(),self.use_ocr.get(),self.ocr_names.get(self.ocr_lang.get(),'tur+eng'))
        if item['status']=='done':item['status']='pending'
        self.row(self.current);self.select()
    def open_extras(self):
        from .extras import ExtraWindow
        source=self.items[self.current]['info'].path if self.current in self.items else None
        ExtraWindow(self,self.lang,source,self.output,theme_name=self.active_theme)

    def remove(self):
        if self.current:self.tree.delete(self.current);del self.items[self.current];self.current=None;self.select();self.controls(True)
    def clear(self):
        for ident in list(self.items):self.tree.delete(ident)
        self.items.clear();self.current=None;self.select();self.controls(True)
    def choose_output(self):
        path=filedialog.askdirectory(parent=self,title=self.t('choose'),initialdir=str(self.output if self.output.exists() else Path.home()))
        if path:self.output=Path(path);self.path_label.configure(text=path);self.save()
    def open_output(self):
        try:
            self.output.mkdir(parents=True,exist_ok=True)
            if sys.platform=='win32':os.startfile(str(self.output))
            else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(self.output)])
        except Exception as e:messagebox.showerror(self.t('error'),str(e),parent=self)
    def controls(self,enabled):
        for w in (self.add_btn,self.folder_add_btn,self.apply_all_check,self.remove_btn,self.clear_btn,self.folder_btn,self.extras_btn):w.state(['!disabled' if enabled else 'disabled'])
        self.start_btn.state(['!disabled' if enabled and self.items else 'disabled'])
        self.select()
    def start(self):
        if self.running or self.detecting:return
        if self.apply_all.get() and self.current in self.items:
            selected=self.items[self.current];target=selected['target'];options=selected['options']
            for ident,item in self.items.items():
                if target not in core.targets(item['info']):continue
                if item['target']!=target or item['options']!=options:
                    item.update(target=target,options=core.Options(**vars(options)),status='pending',result=None);self.row(ident)
        todo=[ident for ident,i in self.items.items() if i['status']!='done']
        if not todo:return
        self.running=True;self.stopping=False;self.runner=core.Runner();self.controls(False);self.stop_btn.state(['!disabled']);self.status.configure(text=self.t('busy'));self.progress.configure(value=0)
        def worker():
            counts={'done':0,'failed':0,'cancelled':0}
            for index,ident in enumerate(todo):
                item=self.items[ident]
                if self.stopping:self.events.put(('state',(ident,'cancelled')));counts['cancelled']+=1;continue
                self.events.put(('state',(ident,'running')))
                self.runner.progress=lambda frac,i=index:self.events.put(('progress',(i+frac)/len(todo)))
                try:
                    self.runner.notes.clear()
                    result=self.runner.convert(item['info'],item['target'],self.output,item['options']);item['result']=result
                    self.logs.append(f"✓ {item['info'].path}\n  → {result}\n");state='done'
                    for note in self.runner.notes:
                        if note[0]=='auto_ocr':self.logs.append('  ℹ '+self.t('auto_ocr').format(pages=note[1],total=note[2]))
                except core.Cancelled:state='cancelled'
                except Exception as e:self.logs.append(f"✗ {item['info'].path}\n{self.error_text(e)}\n{getattr(e,'detail','')}");state='failed'
                counts[state]+=1;self.events.put(('state',(ident,state)))
            self.events.put(('finished',counts))
        threading.Thread(target=worker,daemon=True).start()
    def cancel(self):
        self.stopping=True
        if self.runner:self.runner.cancel()
        self.stop_btn.state(['disabled'])
    def drain(self):
        while True:
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=='detected':self.detected(*data)
            elif kind=='progress':
                if self.progress['mode']=='determinate':self.progress.configure(value=data)
            elif kind=='state':
                ident,state=data;self.items[ident]['status']=state;self.row(ident)
                if state=='running':
                    self.progress.stop();media=self.items[ident]['info'].kind in {'audio','video'}
                    self.progress.configure(mode='determinate' if media else 'indeterminate')
                    if not media:self.progress.start(12)
            elif kind=='finished':
                self.running=False;self.runner=None;self.progress.stop();self.progress.configure(mode='determinate',value=1 if not data['cancelled'] else 0)
                self.stop_btn.state(['disabled']);self.controls(True);self.status.configure(text=self.t('summary').format(**data))
                if data['done'] and not data['failed'] and not data['cancelled']:
                    self.status.configure(text=self.t('complete')+' '+self.t('summary').format(**data))
                    d=self.completion_dialog=tk.Toplevel(self);d.title(self.t('done'));d.transient(self)
                    ttk.Label(d,text='✓  '+self.t('complete'),style='Section.TLabel',padding=(24,20,24,6)).pack(fill='x')
                    ttk.Label(d,text=self.t('summary').format(**data),style='CardHint.TLabel',padding=(24,0,24,16)).pack(fill='x')
                    bar=ttk.Frame(d,style='CardInner.TFrame',padding=(24,0,24,18));bar.pack(fill='x')
                    ttk.Button(bar,text=self.t('close'),command=d.destroy).pack(side='right')
                    ttk.Button(bar,text=self.t('open'),style='Start.TButton',command=lambda:(d.destroy(),self.open_output())).pack(side='right',padx=(0,8))
                    d.configure(bg=theme.PALETTES[self.active_theme]['surface'])
        self.after(80,self.drain)
    def error_text(self,e):return self.t(e.code)+(': '+e.detail if e.code in {'missing_tool','unsupported','not_file'} else '') if isinstance(e,core.ConversionError) else str(e)
    def show_tools(self):messagebox.showinfo(self.t('dependency_title'),'\n'.join(name+' — '+self.t('available' if ok else 'missing') for name,ok in core.tools().items()),parent=self)
    def show_log(self):
        d=tk.Toplevel(self);d.title(self.t('details'));d.geometry('780x440')
        p=theme.PALETTES[self.active_theme]
        text=tk.Text(d,wrap='word',bg=p['surface'],fg=p['text'],relief='flat',padx=12,pady=10,font=(self.font,10));text.pack(fill='both',expand=True);text.insert('1.0','\n'.join(self.logs) or self.t('ready'));text.configure(state='disabled')
    def close(self):
        if self.running:
            if not messagebox.askyesno(self.t('quit_title'),self.t('quit_text'),parent=self):return
            self.cancel()
        self.save();self.destroy()

def main(paths=None):
    Window(paths if paths is not None else sys.argv[1:]).mainloop()
if __name__=='__main__':main()
