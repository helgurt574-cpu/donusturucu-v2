package org.local.donusturucu;
import android.graphics.*;import java.io.*;import java.util.*;import org.json.*;

/** Release smoke test that makes its own inputs: media, subtitles (burned and soft), OCR and speech.
 *  adb shell am start -n org.local.donusturucu/.MainActivity --ez release_test true */
final class ReleaseSelfTest {
 interface Step{String run()throws Exception;}
 static List<String> list(String...x){return new ArrayList<String>(Arrays.asList(x));}
 static void step(MainActivity a,File root,JSONArray rows,String name,Step s)throws Exception{
  JSONObject row=new JSONObject();row.put("action",name);long t=System.currentTimeMillis();a.message("Test: "+name);
  try{row.put("detail",s.run());row.put("pass",true);}catch(Throwable e){row.put("pass",false);row.put("error",e.toString());}
  row.put("ms",System.currentTimeMillis()-t);rows.put(row);FeatureSelfTest.write(root,rows);
 }
 static int[] strip(MainActivity a,File video,File png)throws Exception{
  a.execute(list("ffmpeg","-v","error","-ss","1","-i",video.getAbsolutePath(),"-frames:v","1","-vf","crop=iw:ih/4:0:ih*3/4","-y",png.getAbsolutePath()));
  Bitmap b=BitmapFactory.decodeFile(png.getAbsolutePath());int[]px=new int[b.getWidth()*b.getHeight()];b.getPixels(px,0,b.getWidth(),0,0,b.getWidth(),b.getHeight());return px;
 }
 static void run(final MainActivity a)throws Exception{
  final File root=new File(a.getExternalFilesDir(null),"release-test");root.mkdirs();final JSONArray rows=new JSONArray();
  final File video=new File(root,"video.mp4");final File srt=new File(root,"alt.srt");
  final MediaEngine.Host host=new MediaEngine.Host(){public void run(List<String>args)throws Exception{a.execute(args);}public void check(){}};
  step(a,root,rows,"ffmpeg:create",new Step(){public String run()throws Exception{
   a.execute(list("ffmpeg","-v","error","-f","lavfi","-i","testsrc=s=640x360:r=25:d=3","-f","lavfi","-i","sine=frequency=440:duration=3","-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-y",video.getAbsolutePath()));
   if(video.length()==0)throw new IOException("no video");return video.length()+" bytes";}});
  step(a,root,rows,"media:mp4->mp3",new Step(){public String run()throws Exception{
   MediaEngine.Job j=new MediaEngine.Job();j.source=video;j.info=a.probe(video);j.action="convert";j.format="mp3";
   File out=new MediaEngine(host,new File(root,"mp3")).execute(j).get(0);if(out.length()==0)throw new IOException("empty");return out.getName();}});
  Writer w=new OutputStreamWriter(new FileOutputStream(srt),"UTF-8");w.write("1\n00:00:00,200 --> 00:00:02,500\nMerhaba — Silav! Çğış\n\n");w.close();
  step(a,root,rows,"subtitle:burn",new Step(){public String run()throws Exception{
   MediaEngine.Job j=new MediaEngine.Job();j.source=video;j.info=a.probe(video);j.action="subtitle";j.format="burn";j.other=srt;
   File out=new MediaEngine(host,new File(root,"burn")).execute(j).get(0);
   int[]before=strip(a,video,new File(root,"before.png")),after=strip(a,out,new File(root,"after.png"));int changed=0;
   for(int i=0;i<Math.min(before.length,after.length);i++)if(Math.abs(Color.red(before[i])-Color.red(after[i]))>40)changed++;
   double ratio=changed/(double)before.length;if(ratio<0.002)throw new IOException("subtitle not visible: "+ratio);return "visible "+String.format(Locale.US,"%.3f",ratio);}});
  step(a,root,rows,"subtitle:soft",new Step(){public String run()throws Exception{
   MediaEngine.Job j=new MediaEngine.Job();j.source=video;j.info=a.probe(video);j.action="subtitle";j.format="soft";j.other=srt;
   File out=new MediaEngine(host,new File(root,"soft")).execute(j).get(0);
   String streams=a.execute(list("ffprobe","-v","error","-show_entries","stream=codec_type","-of","csv=p=0",out.getAbsolutePath()));
   if(!streams.contains("subtitle"))throw new IOException("no subtitle stream: "+streams);return streams.replace('\n',' ').trim();}});
  step(a,root,rows,"audio:mp3 mute_range keeps mp3",new Step(){public String run()throws Exception{
   File mp3=new File(root,"tone.mp3");a.execute(list("ffmpeg","-v","error","-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","libmp3lame","-y",mp3.getAbsolutePath()));
   MediaEngine.Job j=new MediaEngine.Job();j.source=mp3;j.info=a.probe(mp3);j.action="mute_range";j.start=1;j.end=2;
   File out=new MediaEngine(host,new File(root,"mute")).execute(j).get(0);if(!out.getName().endsWith(".mp3")||out.length()==0)throw new IOException("got "+out.getName());return out.getName();}});
  for(final String fmt:new String[]{"wav","flac","ogg","m4a"})step(a,root,rows,"audio:mp3->"+fmt,new Step(){public String run()throws Exception{
   File mp3=new File(root,"tone.mp3");MediaEngine.Job j=new MediaEngine.Job();j.source=mp3;j.info=a.probe(mp3);j.action="convert";j.format=fmt;
   File out=new MediaEngine(host,new File(root,"conv-"+fmt)).execute(j).get(0);if(!out.getName().endsWith("."+fmt)||out.length()==0)throw new IOException("got "+out.getName());return out.getName();}});
  step(a,root,rows,"ocr:eng",new Step(){public String run()throws Exception{
   Bitmap b=Bitmap.createBitmap(900,200,Bitmap.Config.ARGB_8888);b.eraseColor(Color.WHITE);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setColor(Color.BLACK);p.setTextSize(72);p.setTypeface(Typeface.DEFAULT_BOLD);
   new Canvas(b).drawText("OFFLINE OCR TEST",40,130,p);File image=new File(root,"ocr.png");FileOutputStream o=new FileOutputStream(image);b.compress(Bitmap.CompressFormat.PNG,100,o);o.close();
   String text=new OcrEngine(a,new OcrEngine.Host(){public void check(){}public void progress(int n,int total){}}).read(image,"image","eng");
   if(!text.toUpperCase(Locale.ROOT).contains("OCR TEST"))throw new IOException("OCR mismatch: "+text);return text.trim();}});
  step(a,root,rows,"pdf:image-only text uses OCR",new Step(){public String run()throws Exception{
   Bitmap b=Bitmap.createBitmap(1240,300,Bitmap.Config.ARGB_8888);b.eraseColor(Color.WHITE);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setColor(Color.BLACK);p.setTextSize(90);p.setTypeface(Typeface.DEFAULT_BOLD);new Canvas(b).drawText("PICTURE TEXT PAGE",40,180,p);
   android.graphics.pdf.PdfDocument doc=new android.graphics.pdf.PdfDocument();android.graphics.pdf.PdfDocument.Page page=doc.startPage(new android.graphics.pdf.PdfDocument.PageInfo.Builder(620,877,1).create());
   page.getCanvas().drawBitmap(b,null,new Rect(10,100,610,245),null);doc.finishPage(page);File pdf=new File(root,"image-only.pdf");FileOutputStream o=new FileOutputStream(pdf);doc.writeTo(o);o.close();doc.close();
   String text=a.documentText(pdf,"pdf");if(!text.toUpperCase(Locale.ROOT).contains("PICTURE"))throw new IOException("OCR fallback missing: "+text);return text.trim();}});
  step(a,root,rows,"speech:en",new Step(){public String run()throws Exception{
   File input=new File(root,"english.mp3");AndroidSelfTest.copy(a,"english-release.mp3",input);File work=new File(root,"speech");work.mkdirs();
   String text=new SpeechEngine(a,new SpeechEngine.Host(){public void check(){}public void run(List<String>args)throws Exception{a.execute(args);}public void progress(double n,double total){}}).read(input,"en",0,-1,work);
   if(!text.toLowerCase(Locale.ROOT).contains("repeat"))throw new IOException("Speech mismatch: "+text);return text.trim();}});
  int failures=0;for(int i=0;i<rows.length();i++)if(!rows.getJSONObject(i).getBoolean("pass"))failures++;
  a.message("Release tests complete: "+(rows.length()-failures)+"/"+rows.length());
 }
}
