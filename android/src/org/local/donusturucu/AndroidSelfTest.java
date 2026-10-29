package org.local.donusturucu;
import java.io.*;import java.util.*;import android.graphics.*;import android.graphics.pdf.*;import android.os.ParcelFileDescriptor;import org.json.*;
/** Explicit adb-triggered diagnostic; no user files are read or modified. */
public final class AndroidSelfTest {
 static void copy(MainActivity a,String name,File dest)throws Exception {InputStream in=a.getAssets().open("test/"+name);OutputStream out=new FileOutputStream(dest);try{byte[]b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}finally{in.close();out.close();}}
 public static void run(final MainActivity a)throws Exception {
  File root=new File(a.getExternalFilesDir(null),"self-test");root.mkdirs();File video=new File(root,"video.mp4"),audio=new File(root,"audio.wav"),silent=new File(root,"silent.mkv"),odd=new File(root,"odd.mkv");copy(a,"video.mp4",video);copy(a,"audio.wav",audio);copy(a,"silent.mkv",silent);copy(a,"odd.mkv",odd);JSONArray results=new JSONArray();
  final MediaEngine.Host host=new MediaEngine.Host(){public void check(){}public void run(List<String>args)throws Exception{a.execute(args);}};
  for(File source:new File[]{video,audio,silent,odd}){
   MediaEngine.Info info=a.probe(source);List<String>actions=new ArrayList<String>(Arrays.asList("trim","remove","split","merge","speed"));if(info.video){actions.addAll(Arrays.asList("mute","frame","gif","rotate","add"));if(info.audio)actions.addAll(Arrays.asList("extract","replace","mute_range"));}else actions.addAll(Arrays.asList("mute_range","volume","fade_in","fade_out"));
   List<String>formats=new ArrayList<String>();if(info.video)formats.addAll(Arrays.asList("mp4","mkv","webm","mov","avi","mpeg","ts","gif"));if(info.audio)formats.addAll(Arrays.asList("mp3","wav","flac","ogg","opus","m4a","aac","aiff","wma"));
   List<String>jobs=new ArrayList<String>(actions);for(String format:formats)jobs.add("convert:"+format);
   for(String job:jobs){JSONObject row=new JSONObject();row.put("source",source.getName());row.put("action",job);try{
    MediaEngine.Job j=new MediaEngine.Job();j.source=source;j.info=info;j.action=job.startsWith("convert:")?"convert":job;j.format=job.contains(":")?job.split(":")[1]:"mp4";j.start=.5;j.end=1.75;j.part=.55;j.factor=job.equals("rotate")?270:1.5;j.other=job.equals("merge")&&info.video?silent:audio;j.otherInfo=a.probe(j.other);j.audioStart=.25;j.audioEnd=1.15;
    File work=new File(root,"case-"+results.length());List<File>outputs=new MediaEngine(host,work).execute(j);for(File out:outputs){if(out.length()==0)throw new IOException("Empty output");a.execute(new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",out.getAbsolutePath(),"-f","null","-")));}
    row.put("pass",true);
   }catch(Exception e){row.put("pass",false);row.put("error",e.toString());}results.put(row);a.message("Android test: "+results.length()+" · "+job);write(root,results);}
  }
  String original="Merhaba dünya. Silav cîhan!\nمرحبا بالعالم\nسلام دنیا، می‌روم ۱۲۳ (ABC-42)";
  File docs=new File(root,"documents");docs.mkdirs();
  for(String format:new String[]{"txt","md","html","rtf","docx","odt","epub","pdf"}){
   JSONObject row=new JSONObject();row.put("action","document:"+format);try{File out=DocumentEngine.write(original,format,docs);String read=DocumentEngine.read(out,format);if(!read.contains("Merhaba")||!read.contains("Silav"))throw new IOException("Missing Latin text: "+read);if(!format.equals("pdf")&&(!read.contains("مرحبا")||!read.contains("سلام")))throw new IOException("Missing RTL text: "+read);row.put("pass",true);row.put("text",read);
    if(format.equals("pdf")){ParcelFileDescriptor fd=ParcelFileDescriptor.open(out,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer renderer=new PdfRenderer(fd);PdfRenderer.Page page=renderer.openPage(0);Bitmap bmp=Bitmap.createBitmap(page.getWidth()*2,page.getHeight()*2,Bitmap.Config.ARGB_8888);bmp.eraseColor(Color.WHITE);page.render(bmp,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);FileOutputStream png=new FileOutputStream(new File(root,"rtl-preview.png"));bmp.compress(Bitmap.CompressFormat.PNG,100,png);png.close();bmp.recycle();page.close();renderer.close();fd.close();}
   }catch(Exception e){row.put("pass",false);row.put("error",e.toString());}results.put(row);write(root,results);
  }
  JSONObject row=new JSONObject();row.put("action","pdf:split-merge");try{File pdf=new File(docs,"document.pdf");List<File>parts=DocumentEngine.pages(pdf,null,"split",1,docs);List<File>merged=DocumentEngine.pages(parts.get(0),parts.get(0),"merge",1,docs);if(merged.get(0).length()==0)throw new IOException("Empty PDF");row.put("pass",true);}catch(Exception e){row.put("pass",false);row.put("error",e.toString());}results.put(row);write(root,results);a.message("Android test complete: "+results.length());
 }
 public static void documents(MainActivity a)throws Exception {
  File root=new File(a.getExternalFilesDir(null),"document-matrix");root.mkdirs();String original="Merhaba dünya. Silav cîhan!\nمرحبا بالعالم\nسلام دنیا، می‌روم ۱۲۳ (ABC-42)\nC:\\Belgeler\\örnek {a}";String[]formats={"txt","md","html","rtf","docx","odt","epub","pdf"};Map<String,File> sources=new LinkedHashMap<String,File>();
  for(String format:formats){File folder=new File(root,"seed-"+format);folder.mkdirs();sources.put(format,DocumentEngine.write(original,format,folder));}
  JSONArray rows=new JSONArray();
  for(String source:formats)for(String target:formats){JSONObject row=new JSONObject();row.put("action",source+"→"+target);try{String text=DocumentEngine.read(sources.get(source),source);File folder=new File(root,source+"-"+target);folder.mkdirs();File output=DocumentEngine.write(text,target,folder);String result=DocumentEngine.read(output,target);if(!result.contains("Merhaba")||!result.contains("Silav")||!result.contains("مرحبا")||!result.contains("سلام"))throw new IOException("Text mismatch: "+result);if(!result.contains("C:\\Belgeler\\örnek {a}"))throw new IOException("Backslash/brace mismatch: "+result);row.put("pass",true);}catch(Exception e){row.put("pass",false);row.put("error",e.toString());}rows.put(row);write(root,rows);a.message("Android document matrix: "+rows.length());}
 }
 private static void write(File root,JSONArray rows)throws Exception {JSONObject report=new JSONObject();report.put("cases",rows.length());int failures=0;for(int i=0;i<rows.length();i++)if(!rows.getJSONObject(i).getBoolean("pass"))failures++;report.put("failures",failures);report.put("rows",rows);Writer w=new OutputStreamWriter(new FileOutputStream(new File(root,"report.json")),"UTF-8");w.write(report.toString(2));w.close();}
}
