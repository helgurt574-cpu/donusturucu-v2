package org.local.donusturucu;
import java.io.*;
import java.util.*;

/** Local FFmpeg plans shared by Android and host integration tests. */
public final class MediaEngine {
 public interface Host {void run(List<String> args) throws Exception;void check() throws Exception;}
 public static final class Info {public boolean video,audio;public double duration,fps=25;public int width,height;}
 public static final class Job {
  public String action="convert",format="mp4",quality="original";
  public File source,other;public Info info,otherInfo;public double start=0,end=-1,part=60,factor=1,audioStart=0,audioEnd=-1;
 }
 private final Host host;private final File work;
 public MediaEngine(Host host,File work){this.host=host;this.work=work;work.mkdirs();}
 static String n(double x){return String.format(Locale.US,"%.6f",x);}
 static List<String> list(String...x){return new ArrayList<String>(Arrays.asList(x));}
 private void ff(List<String> a)throws Exception {host.check();a.add(0,"ffmpeg");a.add(1,"-hide_banner");a.add(2,"-loglevel");a.add(3,"error");a.add(4,"-nostdin");a.addAll(5,list("-filter_complex_threads","1","-filter_threads","1","-threads","2"));a.add("-progress");a.add("pipe:1");a.add("-y");host.run(a);}
 private void input(List<String>a,File f){a.addAll(list("-protocol_whitelist","file,pipe","-i",f.getAbsolutePath()));}
 private void video(List<String>a,String quality,String filter){a.addAll(list("-c:v","libx264","-preset","fast","-crf",quality.equals("high")?"18":quality.equals("small")?"28":"20","-pix_fmt","yuv420p","-vf",filter+",pad=ceil(iw/2)*2:ceil(ih/2)*2","-c:a","aac"));}
 private File clip(File src,Info info,double start,double end,String name,Info shape)throws Exception {
  File out=new File(work,name+(info.video?".mp4":".wav"));List<String>a=list();input(a,src);
  if(shape!=null&&!info.audio)a.addAll(list("-f","lavfi","-i","anullsrc=r=48000:cl=stereo"));
  a.addAll(list("-ss",n(start),"-t",n(end-start)));
  if(info.video){a.addAll(list("-map","0:v:0","-map",info.audio?"0:a:0":shape!=null?"1:a:0":"0:a:0?"));
   String filter="null";if(shape!=null){int w=(shape.width+1)/2*2,h=(shape.height+1)/2*2;filter="scale="+w+":"+h+":force_original_aspect_ratio=decrease,pad="+w+":"+h+":(ow-iw)/2:(oh-ih)/2,setsar=1,fps="+n(shape.fps);}
   video(a,"high",filter);a.addAll(list("-ar","48000","-ac","2"));
  }else a.addAll(list("-map","0:a:0","-vn","-c:a","pcm_s16le","-ar","48000","-ac","2"));
  a.add(out.getAbsolutePath());ff(a);if(!out.isFile()||out.length()==0)throw new IOException("Empty media output");return out;
 }
 private File join(List<File> files,boolean video,String name)throws Exception {
  File manifest=new File(work,name+".txt");Writer w=new OutputStreamWriter(new FileOutputStream(manifest),"UTF-8");
  for(File f:files)w.write("file '"+f.getName()+"'\n");w.close();File out=new File(work,name+(video?".mp4":".wav"));
  ff(list("-f","concat","-safe","1","-protocol_whitelist","file,pipe","-i",manifest.getAbsolutePath(),"-c","copy",out.getAbsolutePath()));return out;
 }
 public static Job copy(Job source){Job j=new Job();j.source=source.source;j.other=source.other;j.info=source.info;j.otherInfo=source.otherInfo;j.action=source.action;j.format=source.format;j.quality=source.quality;j.start=source.start;j.end=source.end;j.part=source.part;j.factor=source.factor;j.audioStart=source.audioStart;j.audioEnd=source.audioEnd;return j;}
 public List<File> mergeMany(List<File> sources,List<Info> infos)throws Exception{if(sources.size()<2)throw new IOException("Choose two files");List<File>parts=new ArrayList<File>();Info shape=infos.get(0);for(int i=0;i<sources.size();i++){host.check();if(infos.get(i).video!=shape.video)throw new IOException("Incompatible media");parts.add(clip(sources.get(i),infos.get(i),0,infos.get(i).duration,"batch-"+i,shape.video?shape:null));}return Arrays.asList(join(parts,shape.video,"merged"));}
 /** Audio edits run in WAV; return them in the user's format (MP3 in → MP3 out). */
 public List<File> execute(Job j)throws Exception {
  List<File> raw=executeRaw(j);
  // Only edits keep the input format; a format the user chose (MP3 → WAV) is never overridden.
  if(j.action.equals("convert")||j.info==null||j.info.video||j.source==null)return raw;
  String name=j.source.getName().toLowerCase(Locale.ROOT);String ext=name.contains(".")?name.substring(name.lastIndexOf('.')+1):"";
  String codec=ext.equals("mp3")?"libmp3lame":ext.equals("m4a")||ext.equals("aac")?"aac":ext.equals("ogg")?"libvorbis":ext.equals("opus")?"libopus":ext.equals("flac")?"flac":null;
  if(codec==null)return raw;List<File> kept=new ArrayList<File>();
  for(File f:raw){if(!f.getName().endsWith(".wav")){kept.add(f);continue;}File out=new File(f.getParentFile(),f.getName().replaceAll("\\.wav$","")+"."+ext);
   List<String>a=list();input(a,f);a.addAll(list("-vn","-c:a",codec));if(codec.equals("libmp3lame"))a.addAll(list("-q:a","2"));a.add(out.getAbsolutePath());ff(a);kept.add(out);}
  return kept;
 }
 public List<File> executeRaw(Job j)throws Exception {
  if(j.source==null||j.info==null)throw new IllegalArgumentException("Choose a file");
  double duration=j.info.duration,start=j.start,end=j.end<0?duration:j.end;
  if(!finite(start)||!finite(end)||start<0||start>=end||end>duration+.06)throw new IllegalArgumentException("Invalid time interval");
  end=Math.min(duration,end);String action=j.action;boolean v=j.info.video;File out=new File(work,"result."+(v?"mp4":"wav"));List<String>a=list();List<File> parts=new ArrayList<File>();
  if(action.equals("trim"))return Arrays.asList(clip(j.source,j.info,start,end,"trim",null));
  if(action.equals("split")){
   if(j.part<.05||Math.ceil((end-start)/j.part)>1000)throw new IllegalArgumentException("Invalid part duration");
   for(int i=0;i<Math.ceil((end-start)/j.part-1e-9);i++)parts.add(clip(j.source,j.info,start+i*j.part,Math.min(end,start+(i+1)*j.part),"part-"+i,null));return parts;
  }
  if(action.equals("remove")){
   if(start>0)parts.add(clip(j.source,j.info,0,start,"before",v?j.info:null));
   if(end<duration)parts.add(clip(j.source,j.info,end,duration,"after",v?j.info:null));
   if(parts.isEmpty())throw new IllegalArgumentException("Empty result");return Arrays.asList(join(parts,v,"removed"));
  }
  if(action.equals("merge")){
   if(j.other==null||j.otherInfo==null||v!=j.otherInfo.video)throw new IllegalArgumentException("Choose a compatible second file");
   parts.add(clip(j.source,j.info,0,duration,"first",v?j.info:null));parts.add(clip(j.other,j.otherInfo,0,j.otherInfo.duration,"second",v?j.info:null));return Arrays.asList(join(parts,v,"merged"));
  }
  if(action.equals("speed")){
   if(!finite(j.factor)||j.factor<.5||j.factor>2)throw new IllegalArgumentException("Speed must be 0.5–2");
   if(start>0)parts.add(clip(j.source,j.info,0,start,"before",null));File mid=clip(j.source,j.info,start,end,"middle",null);File changed=new File(work,"changed."+(v?"mp4":"wav"));input(a,mid);
   if(v){video(a,j.quality,"setpts=(PTS-STARTPTS)/"+n(j.factor));if(j.info.audio)a.addAll(list("-af","atempo="+n(j.factor)));}
   else a.addAll(list("-af","atempo="+n(j.factor),"-c:a","pcm_s16le","-ar","48000","-ac","2"));
   a.addAll(list("-t",n((end-start)/j.factor),changed.getAbsolutePath()));ff(a);parts.add(changed);
   if(end<duration)parts.add(clip(j.source,j.info,end,duration,"after",null));return Arrays.asList(join(parts,v,"speed"));
  }
  if(action.equals("extract")){
   out=new File(work,"audio.mp3");input(a,j.source);a.addAll(list("-ss",n(start),"-t",n(end-start),"-vn","-c:a","libmp3lame","-q:a","2",out.getAbsolutePath()));ff(a);return Arrays.asList(out);
  }
  if(action.equals("frame")){
   out=new File(work,"frame.png");input(a,j.source);a.addAll(list("-ss",n(start),"-frames:v","1",out.getAbsolutePath()));ff(a);return Arrays.asList(out);
  }
  if(action.equals("gif")){
   out=new File(work,"animation.gif");input(a,j.source);a.addAll(list("-ss",n(start),"-t",n(end-start),"-an","-vf","fps=10,scale=480:-1:flags=lanczos",out.getAbsolutePath()));ff(a);return Arrays.asList(out);
  }
  if(action.equals("rotate")){
   if(j.factor!=90&&j.factor!=180&&j.factor!=270)throw new IllegalArgumentException("Invalid rotation");
   File selected=clip(j.source,j.info,start,end,"selected",null);input(a,selected);video(a,j.quality,j.factor==180?"hflip,vflip":j.factor==90?"transpose=1":"transpose=2");a.add(out.getAbsolutePath());ff(a);return Arrays.asList(out);
  }
  if(action.equals("add")||action.equals("replace")){
   if(j.other==null||j.otherInfo==null||j.otherInfo.video||!j.otherInfo.audio)throw new IllegalArgumentException("Choose audio");
   double ae=j.audioEnd<0?j.otherInfo.duration:j.audioEnd;if(j.audioStart<0||j.audioStart>=ae||ae>j.otherInfo.duration+.06)throw new IllegalArgumentException("Invalid audio interval");
   double take=Math.min(ae-j.audioStart,end-start),length=end-start;
   File selectedAudio=new File(work,"insert-audio.wav");a=list("-ss",n(j.audioStart),"-t",n(take));input(a,j.other);a.addAll(list("-af","apad=whole_dur="+n(length),"-t",n(length),"-c:a","pcm_s16le","-ar","48000","-ac","2",selectedAudio.getAbsolutePath()));ff(a);
   if(start>0)parts.add(clip(j.source,j.info,0,start,"before",j.info));File middle=clip(j.source,j.info,start,end,"middle",j.info);File changed=new File(work,"inserted.mp4");a=list();input(a,middle);input(a,selectedAudio);
   if(action.equals("add")){a.addAll(list("-filter_complex","[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]","-map","0:v:0","-map","[a]"));}
   else a.addAll(list("-map","0:v:0","-map","1:a:0"));
   a.addAll(list("-c:v","copy","-c:a","aac","-ar","48000","-ac","2","-t",n(length),changed.getAbsolutePath()));ff(a);parts.add(changed);
   if(end<duration)parts.add(clip(j.source,j.info,end,duration,"after",j.info));return Arrays.asList(join(parts,true,"audio-inserted"));
  }
  if(action.equals("subtitle")){
   if(j.other==null||!j.other.isFile())throw new IllegalArgumentException("Choose a subtitle file");
   String name=j.other.getName().toLowerCase(Locale.ROOT);String ext=name.endsWith(".ass")?"ass":name.endsWith(".ssa")?"ssa":name.endsWith(".vtt")?"vtt":"srt";
   File sub=new File(work,"subtitle."+ext);copyFile(j.other,sub);
   if(j.format.equals("soft")){
    // Separate, switchable track: no re-encode unless the source codecs cannot live in MP4.
    List<String> base=list();input(base,j.source);input(base,sub);base.addAll(list("-map","0:v:0","-map","0:a?","-map","1:0","-c:s","mov_text","-disposition:s:0","default"));
    a=new ArrayList<String>(base);a.addAll(list("-c:v","copy","-c:a","copy",out.getAbsolutePath()));
    try{ff(a);}catch(Exception copyFailed){host.check();a=new ArrayList<String>(base);video(a,j.quality,"null");a.add(out.getAbsolutePath());ff(a);}
   }else{
    // Burned in: Android's own fonts cover Latin, Turkish, Kurdish and Arabic script.
    String filter="subtitles=filename='"+sub.getAbsolutePath().replace(":","\\:")+"':charenc=UTF-8:fontsdir='/system/fonts'"+(ext.equals("srt")||ext.equals("vtt")?":force_style='FontName=Roboto'":"");
    input(a,j.source);a.addAll(list("-map","0:v:0","-map","0:a?","-sn"));video(a,j.quality,filter);a.add(out.getAbsolutePath());ff(a);
   }
   if(!out.isFile()||out.length()==0)throw new IOException("Empty media output");return Arrays.asList(out);
  }
  if(action.equals("convert")){
   out=new File(work,"converted."+j.format);input(a,j.source);
   if(Arrays.asList("mp3","wav","flac","ogg","opus","m4a","aac","aiff","wma").contains(j.format)){
    if(!j.info.audio)throw new IllegalArgumentException("No audio track");a.add("-vn");
    String codec=j.format.equals("mp3")?"libmp3lame":j.format.equals("wav")?"pcm_s16le":j.format.equals("flac")?"flac":j.format.equals("ogg")?"libvorbis":j.format.equals("opus")?"libopus":j.format.equals("aiff")?"pcm_s16be":j.format.equals("wma")?"wmav2":"aac";
    a.addAll(list("-c:a",codec));
   }else{
    if(!v)throw new IllegalArgumentException("Audio input cannot become video");
    if(j.format.equals("gif"))a.addAll(list("-an","-vf","fps=10,scale=480:-1"));
    else if(j.format.equals("webm"))a.addAll(list("-c:v","libvpx-vp9","-crf","30","-b:v","0","-c:a","libopus"));
    else if(j.format.equals("avi"))a.addAll(list("-c:v","mpeg4","-q:v","3","-c:a","libmp3lame","-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2"));
    else if(j.format.equals("mpeg"))a.addAll(list("-c:v","mpeg2video","-q:v","3","-c:a","mp2","-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2"));
    else video(a,j.quality,"null");
   }
   a.add(out.getAbsolutePath());ff(a);return Arrays.asList(out);
  }
  input(a,j.source);
  if(action.equals("mute")){a.addAll(list("-map","0:v:0","-an"));video(a,j.quality,"null");}
  else{
   String filter;
   if(action.equals("mute_range"))filter="volume=0:enable='between(t,"+n(start)+","+n(end)+")'";
   else if(action.equals("volume")){if(!finite(j.factor)||j.factor<0||j.factor>3)throw new IllegalArgumentException("Invalid volume");filter="volume="+n(j.factor)+":enable='between(t,"+n(start)+","+n(end)+")'";}
   else if(action.equals("fade_in")||action.equals("fade_out"))filter="afade=t="+(action.equals("fade_in")?"in":"out")+":st="+n(start)+":d="+n(end-start)+":enable='between(t,"+n(start)+","+n(end)+")'";
   else throw new IllegalArgumentException("Unsupported action");
   a.addAll(list("-af",filter));if(v)video(a,j.quality,"null");else a.addAll(list("-c:a","pcm_s16le"));
  }
  a.add(out.getAbsolutePath());ff(a);return Arrays.asList(out);
 }
 private static void copyFile(File from,File to)throws IOException{InputStream in=new FileInputStream(from);try{OutputStream o=new FileOutputStream(to);try{byte[]b=new byte[65536];int n;while((n=in.read(b))>0)o.write(b,0,n);}finally{o.close();}}finally{in.close();}}
 public static boolean finite(double x){return !Double.isNaN(x)&&!Double.isInfinite(x);}
 public static double seconds(String text)throws Exception {
  String[]parts=text.trim().replace(',','.').split(":",-1);if(parts.length>3)throw new IllegalArgumentException("Invalid time");double value=0;
  for(int i=0;i<parts.length;i++){double x=Double.parseDouble(parts[i]);if(!finite(x)||x<0||(i>0&&x>=60)||(i<parts.length-1&&x!=Math.floor(x)))throw new IllegalArgumentException("Invalid time");value=value*60+x;}return value;
 }
}
