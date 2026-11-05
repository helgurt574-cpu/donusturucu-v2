package org.local.donusturucu;
import java.io.*;
import java.util.*;

/** Local FFmpeg plans shared by Android and host integration tests. */
public final class MediaEngine {
 public interface Host {void run(List<String> args) throws Exception;void check() throws Exception;}
 public static final class Info {public boolean video,audio;public double duration,fps=25;public int width,height,rotation;
  /** Frame size as players show it (phone videos store portrait as rotated landscape). */
  public int shownWidth(){return rotation%180==0?width:height;}public int shownHeight(){return rotation%180==0?height:width;}}
 public static final class Job {
  public String action="convert",format="mp4",quality="original";
  public File source,other;public Info info,otherInfo;public double start=0,end=-1,part=60,factor=1,audioStart=0,audioEnd=-1;
  /** Options of the newer tools: regions, mode, level, cleaning flags, size. */
  public Map<String,String> opts=new HashMap<String,String>();
  public String opt(String key,String fallback){String v=opts.get(key);return v==null||v.length()==0?fallback:v;}
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
 public static Job copy(Job source){Job j=new Job();j.source=source.source;j.other=source.other;j.info=source.info;j.otherInfo=source.otherInfo;j.action=source.action;j.format=source.format;j.quality=source.quality;j.start=source.start;j.end=source.end;j.part=source.part;j.factor=source.factor;j.audioStart=source.audioStart;j.audioEnd=source.audioEnd;j.opts=new HashMap<String,String>(source.opts);return j;}
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
  if(action.equals("watermark")){
   input(a,j.source);a.addAll(list("-map","0:v:0","-map","0:a?"));video(a,j.quality,logoFilter(regions(j.opt("regions","")),j.info.shownWidth(),j.info.shownHeight(),j.opt("mode","fill")));
   a.add(out.getAbsolutePath());ff(a);return Arrays.asList(out);
  }
  if(action.equals("denoise")){
   if(!j.info.audio)throw new IllegalArgumentException("No audio track");String chain=cleanChain(j);
   if(!v){input(a,j.source);a.addAll(list("-map","0:a:0","-vn","-af",chain,"-c:a","pcm_s16le","-ar","48000",out.getAbsolutePath()));ff(a);return Arrays.asList(out);}
   // The picture is copied untouched; only the sound is cleaned.
   List<String> base=list();input(base,j.source);base.addAll(list("-map","0:v:0","-map","0:a:0","-af",chain,"-c:a","aac","-b:a","192k","-ar","48000"));
   a=new ArrayList<String>(base);a.addAll(list("-c:v","copy",out.getAbsolutePath()));
   try{ff(a);}catch(Exception copyFailed){host.check();a=new ArrayList<String>(base);a.addAll(list("-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2",out.getAbsolutePath()));ff(a);}
   return Arrays.asList(out);
  }
  if(action.equals("compress")){
   int level=Integer.parseInt(j.opt("level","2")),limit=Integer.parseInt(j.opt("height","0"));
   String scale=limit<=0?"null":"scale=w='if(gt(iw,ih),-2,min(iw,"+limit+"))':h='if(gt(iw,ih),min(ih,"+limit+"),-2)'";
   input(a,j.source);a.addAll(list("-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","faster","-crf",level==1?"23":level==3?"31":"27","-pix_fmt","yuv420p","-vf",scale+",pad=ceil(iw/2)*2:ceil(ih/2)*2","-c:a","aac","-b:a",level==3?"64k":level==1?"128k":"96k","-movflags","+faststart",out.getAbsolutePath()));ff(a);
   return Arrays.asList(out);
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
 /** Short piece of a file for previews; video is re-encoded upright, sound becomes WAV. */
 public File sample(File src,Info info,double start,double length,String name)throws Exception{double s=Math.max(0,Math.min(start,Math.max(0,info.duration-.2)));return clip(src,info,s,Math.min(info.duration,s+length),name,null);}
 /** One still image of a video, upright, at most maxWidth pixels wide. */
 public File still(File src,double at,int maxWidth,String name)throws Exception{File out=new File(work,name+".jpg");List<String>a=list("-ss",n(Math.max(0,at)));input(a,src);a.addAll(list("-frames:v","1","-vf","scale='min("+maxWidth+",iw)':-2","-q:v","4",out.getAbsolutePath()));ff(a);if(!out.isFile())throw new IOException("No frame");return out;}
 /** Picture (PNG/JPG) with the marked areas filled from their surroundings or blurred. */
 public File cleanPicture(File src,int width,int height,String regions,String mode,String ext)throws Exception{File out=new File(work,"clean."+ext);List<String>a=list();input(a,src);a.addAll(list("-vf",logoFilter(regions(regions),width,height,mode),"-frames:v","1"));if(ext.equals("jpg"))a.addAll(list("-q:v","2"));a.add(out.getAbsolutePath());ff(a);return out;}
 /** "x,y,w,h;…" with values between 0 and 1, relative to the picture as shown. */
 public static List<double[]> regions(String text){List<double[]> out=new ArrayList<double[]>();for(String part:text.split(";")){String[]v=part.trim().split(",");if(v.length!=4)continue;double[]r=new double[4];for(int i=0;i<4;i++)r[i]=Math.max(0,Math.min(1,Double.parseDouble(v[i])));if(r[2]>0.002&&r[3]>0.002)out.add(r);}return out;}
 public static String regionText(List<double[]> regions){StringBuilder b=new StringBuilder();for(double[]r:regions){if(b.length()>0)b.append(';');b.append(String.format(Locale.US,"%.5f,%.5f,%.5f,%.5f",r[0],r[1],r[2],r[3]));}return b.toString();}
 /** delogo needs a border around the area, so the frame is widened by repeating its edges first. */
 static String logoFilter(List<double[]> regions,int width,int height,String mode){
  if(regions.isEmpty())throw new IllegalArgumentException("Choose the watermark area");if(width<8||height<8)throw new IllegalArgumentException("Unknown picture size");
  StringBuilder f=new StringBuilder();boolean blur=mode.equals("blur");
  if(!blur)f.append("pad=iw+4:ih+4:2:2,fillborders=left=2:right=2:top=2:bottom=2:mode=smear");
  int index=0;
  for(double[]r:regions){int x=(int)Math.floor(r[0]*width),y=(int)Math.floor(r[1]*height),w=(int)Math.ceil(r[2]*width),h=(int)Math.ceil(r[3]*height);
   x=Math.max(0,Math.min(width-4,x));y=Math.max(0,Math.min(height-4,y));w=Math.max(4,Math.min(width-x,w));h=Math.max(4,Math.min(height-y,h));
   if(blur){int radius=Math.max(1,Math.min(Math.min(w,h)/2-1,24)),chroma=Math.max(0,Math.min(Math.min(w,h)/4-1,12));String in=index==0?"":"[v"+index+"]";if(index>0)f.append(';');
    f.append(in).append("split[m").append(index).append("][c").append(index).append("];[c").append(index).append("]crop=").append(w).append(':').append(h).append(':').append(x).append(':').append(y).append(",boxblur=luma_radius=").append(radius).append(":luma_power=3:chroma_radius=").append(chroma).append(":chroma_power=3[b").append(index).append("];[m").append(index).append("][b").append(index).append("]overlay=").append(x).append(':').append(y);
    if(index<regions.size()-1)f.append("[v").append(index+1).append(']');}
   else f.append(",delogo=x=").append(x+2).append(":y=").append(y+2).append(":w=").append(w).append(":h=").append(h);
   index++;}
  if(!blur)f.append(",crop=iw-4:ih-4:2:2");return f.toString();
 }
 /** Noise cleaning chain; level 1–3, each kind of noise switched on or off by the user. */
 static String cleanChain(Job j){int level=Integer.parseInt(j.opt("level","2"));List<String> f=new ArrayList<String>();
  if(j.opt("hum","1").equals("1")){f.add("highpass=f="+(level==3?100:80));f.add("bandreject=f=100:width_type=h:w=10");}
  if(j.opt("clicks","1").equals("1")){f.add("adeclick=w=55:o=75:t="+(level==1?"4":level==3?"1.5":"2.5"));if(level>1)f.add("adeclip");}
  if(j.opt("hiss","1").equals("1"))f.add("afftdn=nr="+(level==1?"10":level==3?"28":"18")+":nf="+(level==3?"-30":"-40")+":tn=1");
  if(j.opt("voice","0").equals("1")){f.add("lowpass=f=9000");f.add("dynaudnorm=f=150:g=15");}
  if(j.opt("loud","1").equals("1"))f.add("loudnorm=I=-16:TP=-1.5:LRA=11");
  if(f.isEmpty())throw new IllegalArgumentException("Choose what to clean");return join(f,",");}
 static String join(List<String> parts,String sep){StringBuilder b=new StringBuilder();for(String p:parts){if(b.length()>0)b.append(sep);b.append(p);}return b.toString();}
 private static void copyFile(File from,File to)throws IOException{InputStream in=new FileInputStream(from);try{OutputStream o=new FileOutputStream(to);try{byte[]b=new byte[65536];int n;while((n=in.read(b))>0)o.write(b,0,n);}finally{o.close();}}finally{in.close();}}
 public static boolean finite(double x){return !Double.isNaN(x)&&!Double.isInfinite(x);}
 public static double seconds(String text)throws Exception {
  String[]parts=text.trim().replace(',','.').split(":",-1);if(parts.length>3)throw new IllegalArgumentException("Invalid time");double value=0;
  for(int i=0;i<parts.length;i++){double x=Double.parseDouble(parts[i]);if(!finite(x)||x<0||(i>0&&x>=60)||(i<parts.length-1&&x!=Math.floor(x)))throw new IllegalArgumentException("Invalid time");value=value*60+x;}return value;
 }
}
