"""Shared ttk styling for the Tk windows (extras everywhere, main window on Windows/macOS)."""
from tkinter import ttk,font as tkfont
from . import theme

def pick_font(root):
    families=set(tkfont.families(root))
    return next((f for f in ('Segoe UI','SF Pro Text','Helvetica Neue','Noto Sans','Cantarell','Inter','Ubuntu','DejaVu Sans','Arial') if f in families),'TkDefaultFont')

def apply(root,name,f):
    p=theme.PALETTES[name];s=ttk.Style(root)
    if s.theme_use()!='clam':s.theme_use('clam')
    root.configure(bg=p['bg'])
    for key,value in {'*Background':p['bg'],'*Foreground':p['text'],'*activeBackground':p['surface3'],'*activeForeground':p['text'],
        '*selectBackground':p['selection'],'*selectForeground':p['selection_fg'],'*Entry.Background':p['surface'],'*Listbox.Background':p['surface'],
        '*highlightBackground':p['bg'],'*insertBackground':p['text'],'*TCombobox*Listbox.background':p['surface'],'*TCombobox*Listbox.foreground':p['text'],
        '*TCombobox*Listbox.selectBackground':p['accent'],'*TCombobox*Listbox.selectForeground':p['accent_fg'],'*TCombobox*Listbox.font':(f,10)}.items():
        root.option_add(key,value)
    s.configure('.',background=p['bg'],foreground=p['text'],fieldbackground=p['surface'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'],
        troughcolor=p['trough'],selectbackground=p['selection'],selectforeground=p['selection_fg'],insertcolor=p['text'],focuscolor=p['accent'],arrowcolor=p['muted'],font=(f,10))
    s.configure('Extra.TFrame',background=p['bg'])
    s.configure('Extra.TLabel',background=p['bg'],foreground=p['text'],font=(f,10))
    s.configure('Title.TLabel',background=p['bg'],foreground=p['text'],font=(f,18,'bold'))
    s.configure('Card.TFrame',background=p['surface'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'],relief='solid',borderwidth=1)
    s.configure('CardInner.TFrame',background=p['surface'],borderwidth=0,relief='flat')
    s.configure('CardTitle.TLabel',background=p['surface'],foreground=p['text'],font=(f,11,'bold'))
    s.configure('CardEmpty.TLabel',background=p['surface'],foreground=p['muted'],font=(f,11,'italic'))
    s.configure('CardMeta.TLabel',background=p['surface'],foreground=p['muted'],font=(f,9))
    button=dict(padding=(12,7),font=(f,10),relief='flat',borderwidth=1)
    def flat(name,bg,fg,hover,border=p['border'],pressed=None,**extra):
        s.configure(name,background=bg,foreground=fg,bordercolor=border,lightcolor=bg,darkcolor=bg,**{**button,**extra})
        s.map(name,background=[('disabled',p['disabled_bg']),('pressed',pressed or hover),('active',hover)],
            foreground=[('disabled',p['disabled_fg']),('!disabled',fg)],lightcolor=[('active',hover)],darkcolor=[('active',hover)],
            bordercolor=[('disabled',p['border']),('focus',p['accent'])])
    flat('Extra.TButton',p['surface2'],p['text'],p['surface3'])
    flat('TButton',p['surface2'],p['text'],p['surface3'])
    flat('Accent.TButton',p['accent'],p['accent_fg'],p['accent_hover'],border=p['accent'],pressed=p['accent_active'],font=(f,10,'bold'))
    flat('ExtraStop.TButton',p['danger_soft'],p['danger'],p['danger_active'],border=p['danger_border'])
    flat('Operation.TButton',p['surface'],p['text'],p['surface2'],anchor='w',padding=(12,9))
    flat('ChosenOperation.TButton',p['accent'],p['accent_fg'],p['accent_hover'],border=p['accent'],anchor='w',padding=(12,9),font=(f,10,'bold'))
    s.configure('Extra.TEntry',padding=6,fieldbackground=p['surface'],foreground=p['text'],bordercolor=p['border'],lightcolor=p['surface'],darkcolor=p['surface'])
    s.map('Extra.TEntry',bordercolor=[('focus',p['accent'])],lightcolor=[('focus',p['accent'])],fieldbackground=[('disabled',p['disabled_bg'])],foreground=[('disabled',p['disabled_fg'])])
    s.configure('TCombobox',padding=5,fieldbackground=p['surface'],background=p['surface2'],foreground=p['text'],arrowcolor=p['text'],bordercolor=p['border'],lightcolor=p['surface'],darkcolor=p['surface'])
    s.map('TCombobox',fieldbackground=[('readonly',p['surface']),('disabled',p['disabled_bg'])],foreground=[('disabled',p['disabled_fg']),('readonly',p['text'])],
        selectbackground=[('readonly',p['surface'])],selectforeground=[('readonly',p['text'])],background=[('active',p['surface3'])],bordercolor=[('focus',p['accent'])])
    s.configure('TCheckbutton',background=p['bg'],foreground=p['text'],indicatorbackground=p['surface'],indicatorforeground=p['accent_fg'],font=(f,10),padding=3)
    s.map('TCheckbutton',background=[('active',p['bg'])],indicatorbackground=[('selected',p['accent']),('pressed',p['surface3'])],foreground=[('disabled',p['disabled_fg'])])
    s.configure('Extra.TLabelframe',background=p['bg'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'])
    s.configure('Extra.TLabelframe.Label',background=p['bg'],foreground=p['text'],font=(f,10,'bold'))
    s.configure('Vertical.TScrollbar',background=p['surface3'],troughcolor=p['bg'],bordercolor=p['bg'],lightcolor=p['surface3'],darkcolor=p['surface3'],arrowcolor=p['muted'],gripcount=0)
    s.map('Vertical.TScrollbar',background=[('active',p['muted'])])
    s.configure('Horizontal.TProgressbar',background=p['accent'],troughcolor=p['trough'],bordercolor=p['trough'],lightcolor=p['accent'],darkcolor=p['accent'],thickness=8)
    # Main (portable) window styles.
    s.configure('Card.TLabel',background=p['surface'],foreground=p['text'],font=(f,10))
    s.configure('Hint.TLabel',background=p['bg'],foreground=p['muted'],font=(f,10))
    s.configure('CardHint.TLabel',background=p['surface'],foreground=p['muted'],font=(f,9))
    s.configure('Section.TLabel',background=p['surface'],foreground=p['text'],font=(f,11,'bold'))
    s.configure('Badge.TLabel',background=p['success_soft'],foreground=p['success'],font=(f,9,'bold'),padding=(10,4))
    s.configure('MainTitle.TLabel',background=p['bg'],foreground=p['text'],font=(f,24,'bold'))
    s.configure('TFrame',background=p['bg'])
    s.configure('Card.TCheckbutton',background=p['surface'],foreground=p['text'],indicatorbackground=p['surface'],indicatorforeground=p['accent_fg'],font=(f,10),padding=3)
    s.map('Card.TCheckbutton',background=[('active',p['surface'])],indicatorbackground=[('selected',p['accent']),('pressed',p['surface3'])],foreground=[('disabled',p['disabled_fg'])])
    flat('Start.TButton',p['accent'],p['accent_fg'],p['accent_hover'],border=p['accent'],pressed=p['accent_active'],font=(f,10,'bold'))
    flat('Stop.TButton',p['danger_soft'],p['danger'],p['danger_active'],border=p['danger_border'])
    s.configure('Treeview',background=p['surface'],fieldbackground=p['surface'],foreground=p['text'],rowheight=30,bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'],font=(f,10))
    s.map('Treeview',background=[('selected',p['selection'])],foreground=[('selected',p['selection_fg'])])
    s.configure('Treeview.Heading',background=p['surface2'],foreground=p['muted'],font=(f,9,'bold'),relief='flat',bordercolor=p['border'],lightcolor=p['surface2'],darkcolor=p['surface2'],padding=(8,6))
    s.map('Treeview.Heading',background=[('active',p['surface3'])])
