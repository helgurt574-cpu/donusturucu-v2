"""Plain translation handoff; timing always comes from the original SRT."""
import re
from pathlib import Path

from .core import ConversionError
class SubtitleError(ConversionError):pass
TIME=re.compile(r'^(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})$')
def milliseconds(value):
 m=TIME.fullmatch(value)
 if not m:raise SubtitleError('subtitle_invalid')
 h,mi,s,ms=map(int,m.groups());return ((h*60+mi)*60+s)*1000+ms

def parse(value):
 value=value.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n').strip()
 cues=[]
 for block in re.split(r'\n[ \t]*\n',value):
  lines=block.splitlines()
  if len(lines)<3 or not lines[0].strip().isdigit():raise SubtitleError('subtitle_invalid')
  pair=lines[1].strip().split(' --> ')
  if len(pair)!=2 or milliseconds(pair[1])<=milliseconds(pair[0]):raise SubtitleError('subtitle_invalid')
  text=' '.join(line.strip() for line in lines[2:] if line.strip())
  if not text:raise SubtitleError('subtitle_invalid')
  cues.append((lines[0].strip(),lines[1].strip(),text))
 if not cues:raise SubtitleError('subtitle_invalid')
 return cues

def export_text(source):
 return '\n'.join(text for _,_,text in parse(Path(source).read_text(encoding='utf-8-sig')))+'\n'

def translated_srt(text,original):
 cues=parse(Path(original).read_text(encoding='utf-8-sig'))
 lines=Path(text).read_text(encoding='utf-8-sig').replace('\r\n','\n').replace('\r','\n').strip().split('\n')
 if len(lines)!=len(cues) or any(not line.strip() for line in lines):raise SubtitleError('subtitle_line_count')
 return ''.join(f'{number}\n{timing}\n{line.strip()}\n\n' for (number,timing,_),line in zip(cues,lines))
