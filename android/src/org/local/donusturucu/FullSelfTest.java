package org.local.donusturucu;
import android.graphics.*;import java.io.*;import java.util.*;import org.json.*;

/** Every file type × every operation the screen offers × every output format, through the
 *  same code the Start button runs (MainActivity.produce). Nothing is trimmed or skipped.
 *  adb shell am start -n org.local.donusturucu/.MainActivity --ez full_test true */
final class FullSelfTest {
 static final List<String> AUDIO=Arrays.asList("mp3","wav","flac","ogg","opus","m4a","aac","aiff","wma");
 static void deleteTree(File f){if(f.isDirectory()){File[]c=f.listFiles();if(c!=null)for(File x:c)deleteTree(x);}f.delete();}
 static void ff(MainActivity a,String...args)throws Exception{List<String>l=new ArrayList<String>(Arrays.asList("ffmpeg","-v","error"));l.addAll(Arrays.asList(args));a.execute(l);}
 static File text(File root,String name,String content)throws Exception{File f=new File(root,name);Writer w=new OutputStreamWriter(new FileOutputStream(f),"UTF-8");w.write(content);w.close();return f;}
 static Bitmap words(String s,int w,int h){Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);b.eraseColor(Color.WHITE);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setColor(Color.BLACK);p.setTextSize(h*0.35f);p.setTypeface(Typeface.DEFAULT_BOLD);new Canvas(b).drawText(s,30,h*0.62f,p);return b;}
 static String expected(String action,String format,String inputExt,boolean video,boolean speechSrt){
  if(action.equals("convert")||action.equals("ocr"))return format;if(action.equals("subtitle_text"))return "txt";if(action.equals("subtitle_restore"))return "srt";
  if(action.equals("transcribe"))return speechSrt?"srt":"txt";if(action.equals("extract"))return "mp3";if(action.equals("frame"))return "png";if(action.equals("gif"))return "gif";
  if(inputExt.equals("pdf"))return "pdf";return video?"mp4":inputExt;}
 static String nameExt(File f){String n=f.getName();return n.substring(n.lastIndexOf('.')+1).toLowerCase(Locale.ROOT);}
 static void run(final MainActivity a)throws Exception{
  File root=new File(a.getExternalFilesDir(null),"full-test");deleteTree(root);root.mkdirs();final JSONArray rows=new JSONArray();
  File work=new File(root,"inputs");work.mkdirs();a.message("Tam test: girdiler hazırlanıyor");
  // ---- inputs: one of every kind the app accepts
  File speech=new File(work,"speech.mp3");AndroidSelfTest.copy(a,"english-release.mp3",speech);
  File video=new File(work,"video.mp4");ff(a,"-f","lavfi","-i","testsrc=s=640x360:r=25:d=5","-i",speech.getAbsolutePath(),"-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-y",video.getAbsolutePath());
  File silent=new File(work,"silent.mp4");ff(a,"-f","lavfi","-i","testsrc=s=640x360:r=25:d=4","-c:v","libx264","-pix_fmt","yuv420p","-y",silent.getAbsolutePath());
  File wav=new File(work,"speech.wav");ff(a,"-i",speech.getAbsolutePath(),"-y",wav.getAbsolutePath());
  File m4a=new File(work,"speech.m4a");ff(a,"-i",speech.getAbsolutePath(),"-c:a","aac","-y",m4a.getAbsolutePath());
  String body="Dönüştürücü tam test belgesi.\nMerhaba dünya — Silav cîhan! Çğış ÇĞİŞ 12345\n\nİkinci paragraf: belgeler, sesler ve videolar.\n";
  File txt=text(work,"belge.txt",body);File md=text(work,"belge.md","# Başlık\n\n"+body);File html=text(work,"belge.html","<html><body><h1>Başlık</h1><p>"+body.replace("\n","<br>")+"</p></body></html>");
  List<File> docs=new ArrayList<File>(Arrays.asList(txt,md,html));
  for(String f:new String[]{"docx","odt","rtf","epub","pdf"}){File dir=new File(work,"make-"+f);dir.mkdirs();File made=DocumentEngine.write(body,f,dir);File named=new File(work,"belge."+f);made.renameTo(named);docs.add(named);}
  android.graphics.pdf.PdfDocument pd=new android.graphics.pdf.PdfDocument();for(int i=0;i<2;i++){android.graphics.pdf.PdfDocument.Page page=pd.startPage(new android.graphics.pdf.PdfDocument.PageInfo.Builder(620,877,i+1).create());page.getCanvas().drawBitmap(words("PICTURE PAGE "+(i+1),1200,260),null,new Rect(10,100,610,230),null);pd.finishPage(page);}
  File imagePdf=new File(work,"resim-yazi.pdf");FileOutputStream o=new FileOutputStream(imagePdf);pd.writeTo(o);o.close();pd.close();docs.add(imagePdf);
  File png=new File(work,"foto.png");o=new FileOutputStream(png);words("OFFLINE OCR TEST",1200,260).compress(Bitmap.CompressFormat.PNG,100,o);o.close();
  File srt=text(work,"altyazi.srt","1\n00:00:00,500 --> 00:00:02,000\nMerhaba dünya\n\n2\n00:00:02,500 --> 00:00:04,000\nSilav cîhan\n\n");
  File translated=text(work,"ceviri.txt","Hello world\nHello world again\n");
  // Real-world media: broken tags, cover art, phone HEVC with rotation, extra tracks, other containers.
  List<File> real=new ArrayList<File>();
  for(String n:new String[]{"bozuk-etiket.mp3","kapakli.mp3","kapakli.m4a","etiketli.flac","ses.ogg","telefon-dikey-hevc.mp4","iki-ses-altyazi.mkv","klip.mov","klip.webm","klip.avi"}){File f=new File(work,n);AndroidSelfTest.copy(a,"real-"+n,f);real.add(f);}
  List<File> inputs=new ArrayList<File>(Arrays.asList(video,silent,speech,wav,m4a));inputs.addAll(real);inputs.addAll(docs);inputs.addAll(Arrays.asList(png,srt,translated));
  final MainActivity.ListedFile speechEntry=a.classify(speech,speech.getName(),"mp3"),srtEntry=a.classify(srt,srt.getName(),"srt");
  SpeechEngine speechEngine=new SpeechEngine(a,new SpeechEngine.Host(){public void check()throws Exception{a.check();}public void run(List<String>args)throws Exception{a.execute(args);}public void progress(double c,double t){}},true);
  int total=0,failed=0;
  try{
  for(File input:inputs){
   String name=input.getName();String ext=name.substring(name.lastIndexOf('.')+1);MainActivity.ListedFile entry;
   {total++;JSONObject row=new JSONObject();row.put("case",name+" · tür tanıma");MainActivity.ListedFile found=null;
    try{found=a.classify(input,name,ext);boolean wantAudio=AUDIO.contains(ext.toLowerCase(Locale.ROOT)),wantVideo=Arrays.asList("mp4","mkv","mov","webm","avi").contains(ext.toLowerCase(Locale.ROOT));
     if(wantAudio&&(found.info==null||found.info.video||!found.info.audio))throw new IOException("ses olarak tanınmadı");
     if(wantVideo&&(found.info==null||!found.info.video))throw new IOException("video olarak tanınmadı");
     row.put("pass",true);row.put("detail",found.info==null?found.ext:(found.info.video?"video":"ses")+" "+String.format(Locale.US,"%.1fs",found.info.duration));}
    catch(Throwable e){failed++;row.put("pass",false);row.put("error",String.valueOf(e));}
    rows.put(row);FeatureSelfTest.write(root,rows);if(found==null)continue;entry=found;}
   for(String[] act:MainActivity.offeredActions(entry.info,entry.ext)){String action=act[0];
    List<String[]> variants=new ArrayList<String[]>();// {format, rich, speechSrt, subtitleMode}
    if(action.equals("convert")||action.equals("ocr")){for(String f:MainActivity.formatValues(entry.info,entry.ext)){String fl=f.toLowerCase(Locale.ROOT);variants.add(new String[]{fl,"0","0",""});
      if(action.equals("convert")&&entry.info==null&&Arrays.asList("pdf","docx","odt","epub","html").contains(fl)&&!entry.ext.equals("srt"))variants.add(new String[]{fl,"1","0",""});}}
    else if(action.equals("transcribe")){variants.add(new String[]{"pdf","0","0",""});variants.add(new String[]{"pdf","0","1",""});}
    else if(action.equals("subtitle")){variants.add(new String[]{"burn","0","0",""});variants.add(new String[]{"soft","0","0",""});}
    else variants.add(new String[]{"pdf","0","0",""});
    for(String[] v:variants){total++;JSONObject row=new JSONObject();String label=name+" · "+action+(v[0].equals("pdf")&&!action.equals("convert")&&!action.equals("ocr")?"":" → "+v[0])+(v[1].equals("1")?" (zengin)":"")+(v[2].equals("1")?" (SRT)":"");
     row.put("case",label);long t=System.currentTimeMillis();a.message("Tam test "+total+": "+label);File out=new File(root,"case-"+total);out.mkdirs();
     try{
      MediaEngine.Job j=new MediaEngine.Job();j.source=entry.file;j.info=entry.info;j.action=action;j.format=v[0];j.quality="balanced";
      j.start=action.equals("frame")?1:entry.info!=null?1:0;j.end=entry.info!=null&&!action.equals("frame")?2.5:-1;j.part=1.5;j.factor=action.equals("rotate")?90:action.equals("volume")?0.5:1.5;
      if(Arrays.asList("convert","extract","mute","subtitle","merge").contains(action)){j.start=0;j.end=-1;}
      if(action.equals("transcribe")){j.start=0;j.end=-1;}
      MainActivity.ListedFile partner=null;
      if(action.equals("merge"))partner=entry;if(action.equals("add")||action.equals("replace"))partner=speechEntry;if(action.equals("subtitle"))partner=srtEntry;if(action.equals("subtitle_restore"))partner=srtEntry;
      a.useOther(partner);j.other=partner==null?null:partner.file;j.otherInfo=partner==null?null:partner.info;
      List<File> outputs=a.produce(entry,j,action,v[0],v[1].equals("1"),1,"en",v[2].equals("1"),"eng",speechEngine,out);
      if(outputs==null||outputs.isEmpty())throw new IOException("çıktı yok");
      String want=expected(action,v[0],entry.info!=null?nameExt(input):entry.ext,entry.info!=null&&entry.info.video,v[2].equals("1"));StringBuilder names=new StringBuilder();
      for(File f:outputs){if(!f.isFile()||f.length()==0)throw new IOException("boş çıktı: "+f.getName());if(!f.getName().toLowerCase(Locale.ROOT).endsWith("."+want))throw new IOException("beklenen ."+want+", çıkan "+f.getName());names.append(f.getName()).append(' ');}
      row.put("pass",true);row.put("detail",names.toString().trim());
     }catch(Throwable e){
      // A plain text that is not a line-by-line translation must be refused with a readable message.
      if(action.equals("subtitle_restore")&&input!=translated&&String.valueOf(e.getMessage()).equals("subtitle_line_count")&&MainActivity.imageError("subtitle_line_count",false)!=null){row.put("pass",true);row.put("detail","beklenen uyarı: "+MainActivity.imageError("subtitle_line_count",false));}
      else{failed++;row.put("pass",false);row.put("error",String.valueOf(e));}}
     finally{a.useOther(null);deleteTree(out);}
     row.put("ms",System.currentTimeMillis()-t);rows.put(row);FeatureSelfTest.write(root,rows);
    }
   }
  }
  }finally{speechEngine.close();}
  a.message("Tam test bitti: "+(total-failed)+"/"+total+" geçti");
 }
}
