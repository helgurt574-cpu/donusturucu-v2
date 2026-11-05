package org.local.donusturucu;
import android.graphics.*;
import java.io.*;
import java.util.*;
import org.json.*;
import com.tom_roush.pdfbox.cos.COSName;
import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle;
import com.tom_roush.pdfbox.pdmodel.font.PDType1Font;
import com.tom_roush.pdfbox.pdmodel.graphics.state.PDExtendedGraphicsState;
import com.tom_roush.pdfbox.text.PDFTextStripper;
import com.tom_roush.pdfbox.util.Matrix;

/** The 1.4 tools on real inputs, through MainActivity.produce, with checks on the results.
 *  adb shell am start -n org.local.donusturucu/.MainActivity --ez tools_test true
 *  Report: Android/data/org.local.donusturucu/files/tools-test/report.json */
final class ToolsSelfTest {
 interface Check {String run(List<File> out)throws Exception;}
 static void run(final MainActivity a)throws Exception{
  File root=new File(a.getExternalFilesDir(null),"tools-test");FullSelfTest.deleteTree(root);root.mkdirs();File in=new File(root,"inputs");in.mkdirs();JSONArray rows=new JSONArray();
  a.message("Araç testi: girdiler hazırlanıyor");
  // A video with a white "logo" box in the corner and a noisy, crackling sound.
  File video=new File(in,"logolu.mp4");FullSelfTest.ff(a,"-f","lavfi","-i","testsrc=s=640x360:r=25:d=4","-f","lavfi","-i","sine=f=440:d=4","-f","lavfi","-i","anoisesrc=d=4:c=pink:a=0.08","-filter_complex","[0:v]drawbox=x=20:y=20:w=120:h=50:color=white:t=fill[v];[1:a][2:a]amix=inputs=2:normalize=0[a]","-map","[v]","-map","[a]","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-y",video.getAbsolutePath());
  File noisy=new File(in,"cizirtili.wav");FullSelfTest.ff(a,"-f","lavfi","-i","sine=f=330:d=6","-f","lavfi","-i","anoisesrc=d=6:c=white:a=0.1","-filter_complex","amix=inputs=2:normalize=0","-y",noisy.getAbsolutePath());
  File png=new File(in,"foto.png");Bitmap b=Bitmap.createBitmap(800,500,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);c.drawColor(Color.rgb(90,140,200));Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setColor(Color.WHITE);p.setTextSize(48);c.drawText("© LOGO",560,470,p);FileOutputStream o=new FileOutputStream(png);b.compress(Bitmap.CompressFormat.PNG,100,o);o.close();
  File jpg=new File(in,"foto2.jpg");o=new FileOutputStream(jpg);b.compress(Bitmap.CompressFormat.JPEG,90,o);o.close();b.recycle();
  File pdf=watermarkedPdf(new File(in,"taslak.pdf"));
  final MainActivity.ListedFile v=a.classify(video,video.getName(),"mp4"),s=a.classify(noisy,noisy.getName(),"wav"),im=a.classify(png,png.getName(),"png"),im2=a.classify(jpg,jpg.getName(),"jpg"),doc=a.classify(pdf,pdf.getName(),"pdf");
  int[] n={0};
  test(a,root,rows,n,v,"watermark","pdf",opts("regions","0.02,0.04,0.22,0.17","mode","fill"),new Check(){public String run(List<File> out)throws Exception{return probeVideo(a,out.get(0));}});
  test(a,root,rows,n,v,"watermark","pdf",opts("regions","0.02,0.04,0.22,0.17;0.7,0.7,0.2,0.2","mode","blur"),new Check(){public String run(List<File> out)throws Exception{return probeVideo(a,out.get(0));}});
  test(a,root,rows,n,v,"denoise","pdf",opts("level","3","voice","1"),new Check(){public String run(List<File> out)throws Exception{MediaEngine.Info i=a.probe(out.get(0));if(!i.video||!i.audio)throw new IOException("görüntü veya ses kayboldu");return "video+ses "+i.duration;}});
  test(a,root,rows,n,v,"compress","pdf",opts("level","3","height","240"),new Check(){public String run(List<File> out)throws Exception{MediaEngine.Info i=a.probe(out.get(0));if(i.height>240)throw new IOException("yükseklik "+i.height);return i.width+"x"+i.height+" "+out.get(0).length()+" B";}});
  test(a,root,rows,n,s,"denoise","pdf",opts("level","2"),new Check(){public String run(List<File> out)throws Exception{if(!out.get(0).getName().endsWith(".wav"))throw new IOException(out.get(0).getName());return out.get(0).length()+" B";}});
  for(final String f:new String[]{"jpg","webp","bmp","pdf","png"})test(a,root,rows,n,im,"convert",f,opts("scale","50","q","2"),new Check(){public String run(List<File> out)throws Exception{File r=out.get(0);if(!r.getName().endsWith("."+f))throw new IOException(r.getName());if(!f.equals("pdf")){BitmapFactory.Options bo=new BitmapFactory.Options();bo.inJustDecodeBounds=true;BitmapFactory.decodeFile(r.getAbsolutePath(),bo);if(bo.outWidth!=400)throw new IOException("genişlik "+bo.outWidth);}return r.length()+" B";}});
  test(a,root,rows,n,im2,"edit","pdf",opts("angle","90","gray","1"),new Check(){public String run(List<File> out)throws Exception{File r=out.get(0);if(!r.getName().endsWith(".jpg"))throw new IOException(r.getName());BitmapFactory.Options bo=new BitmapFactory.Options();bo.inJustDecodeBounds=true;BitmapFactory.decodeFile(r.getAbsolutePath(),bo);if(bo.outWidth!=500||bo.outHeight!=800)throw new IOException(bo.outWidth+"x"+bo.outHeight);return "500x800";}});
  test(a,root,rows,n,im,"watermark","pdf",opts("regions","0.68,0.84,0.31,0.15","mode","fill"),new Check(){public String run(List<File> out)throws Exception{Bitmap r=BitmapFactory.decodeFile(out.get(0).getAbsolutePath());try{int px=r.getPixel(640,455);if(Color.red(px)>200&&Color.green(px)>200)throw new IOException("logo duruyor");return "logo alanı arka plan rengi";}finally{r.recycle();}}});
  a.useOther(im2);test(a,root,rows,n,im,"merge","pdf",opts(),new Check(){public String run(List<File> out)throws Exception{int pages=Tools.pageCount(out.get(0));if(pages!=2)throw new IOException(pages+" sayfa");return "2 sayfa";}});a.useOther(null);
  test(a,root,rows,n,doc,"watermark","pdf",opts("auto","1"),new Check(){public String run(List<File> out)throws Exception{String text=text(out.get(0));if(text.contains("DRAFT"))throw new IOException("DRAFT duruyor");if(!text.contains("Body text"))throw new IOException("asıl metin silindi");return "DRAFT silindi, metin duruyor";}});
  test(a,root,rows,n,doc,"watermark","pdf",opts("auto","0","keyword","company confidential"),new Check(){public String run(List<File> out)throws Exception{String text=text(out.get(0));if(text.contains("Company"))throw new IOException("anahtar kelime duruyor");if(!text.contains("Body text"))throw new IOException("asıl metin silindi");return "kelimeyle silindi";}});
  test(a,root,rows,n,doc,"watermark","pdf",opts("auto","0","regions","0.1,0.1,0.3,0.1"),new Check(){public String run(List<File> out)throws Exception{return Tools.pageCount(out.get(0))+" sayfa, alan kapatıldı";}});
  test(a,root,rows,n,doc,"compress","pdf",opts("level","3"),new Check(){public String run(List<File> out)throws Exception{return out.get(0).length()+" B";}});
  test(a,root,rows,n,doc,"pages","pdf",opts("spec","3,1","keep","1"),new Check(){public String run(List<File> out)throws Exception{int pages=Tools.pageCount(out.get(0));if(pages!=2)throw new IOException(pages+" sayfa");if(!text(out.get(0)).trim().startsWith("Body text 3"))throw new IOException("sıra yanlış");return "3,1";}});
  test(a,root,rows,n,doc,"pages","pdf",opts("spec","2","keep","0"),new Check(){public String run(List<File> out)throws Exception{int pages=Tools.pageCount(out.get(0));if(pages!=2)throw new IOException(pages+" sayfa");return "2 silindi";}});
  test(a,root,rows,n,doc,"pdf_rotate","pdf",opts("angle","90","spec","1"),new Check(){public String run(List<File> out)throws Exception{PDDocument d=PDDocument.load(out.get(0));try{if(d.getPage(0).getRotation()!=90||d.getPage(1).getRotation()!=0)throw new IOException("döndürme yanlış");}finally{d.close();}return "1. sayfa 90°";}});
  test(a,root,rows,n,doc,"convert","png",opts("dpi","96"),new Check(){public String run(List<File> out)throws Exception{if(out.size()!=3)throw new IOException(out.size()+" resim");return "3 PNG";}});
  // Previews use the same engine on a short piece: make one the way the screen does.
  {n[0]++;JSONObject row=new JSONObject();row.put("case","önizleme örneği · video");long t=System.currentTimeMillis();try{File w=new File(root,"sample");w.mkdirs();MediaEngine me=new MediaEngine(new MediaEngine.Host(){public void run(List<String> x)throws Exception{a.execute(x);}public void check()throws Exception{a.check();}},w);
    File sample=me.sample(video,v.info,1,2,"sample");MediaEngine.Info si=a.probe(sample);if(Math.abs(si.duration-2)>0.3)throw new IOException("süre "+si.duration);File still=me.still(video,1,320,"still");if(BitmapFactory.decodeFile(still.getAbsolutePath())==null)throw new IOException("kare yok");row.put("pass",true);row.put("detail","örnek "+si.duration+" s, kare tamam");}
   catch(Throwable e){row.put("pass",false);row.put("error",String.valueOf(e));}row.put("ms",System.currentTimeMillis()-t);rows.put(row);FeatureSelfTest.write(root,rows);}
  int failed=0;for(int i=0;i<rows.length();i++)if(!rows.getJSONObject(i).getBoolean("pass"))failed++;
  a.message("Araç testi bitti: "+(rows.length()-failed)+"/"+rows.length()+" geçti");
 }
 static Map<String,String> opts(String...kv){Map<String,String> m=new HashMap<String,String>();for(int i=0;i+1<kv.length;i+=2)m.put(kv[i],kv[i+1]);return m;}
 static void test(MainActivity a,File root,JSONArray rows,int[] n,MainActivity.ListedFile entry,String action,String format,Map<String,String> opts,Check check)throws Exception{
  n[0]++;JSONObject row=new JSONObject();String label=entry.name+" · "+action+(action.equals("convert")?" → "+format:"")+" "+opts;row.put("case",label);a.message("Araç testi "+n[0]+": "+label);long t=System.currentTimeMillis();File out=new File(root,"case-"+n[0]);out.mkdirs();
  try{MediaEngine.Job j=new MediaEngine.Job();j.source=entry.file;j.info=entry.info;j.action=action;j.format=format;j.quality="balanced";j.opts.putAll(opts);
   List<File> files=a.produce(entry,j,action,format,false,1,"tr",false,"eng",null,out);if(files==null||files.isEmpty())throw new IOException("çıktı yok");for(File f:files)if(!f.isFile()||f.length()==0)throw new IOException("boş çıktı "+f.getName());
   row.put("pass",true);row.put("detail",check.run(files));}
  catch(Throwable e){row.put("pass",false);row.put("error",String.valueOf(e));}
  row.put("ms",System.currentTimeMillis()-t);rows.put(row);FeatureSelfTest.write(root,rows);
 }
 static String probeVideo(MainActivity a,File f)throws Exception{MediaEngine.Info i=a.probe(f);if(!i.video||i.width!=640||i.height!=360)throw new IOException("video bozuk "+i.width+"x"+i.height);return "640x360 "+String.format(Locale.ROOT,"%.1f",i.duration)+" s";}
 static String text(File pdf)throws Exception{PDDocument d=PDDocument.load(pdf);try{return new PDFTextStripper().getText(d);}finally{d.close();}}
 /** Three pages of body text, a see-through diagonal DRAFT and a "Company Confidential" footer. */
 static File watermarkedPdf(File out)throws Exception{PDDocument d=new PDDocument();
  try{for(int i=1;i<=3;i++){PDPage page=new PDPage(PDRectangle.A4);d.addPage(page);PDPageContentStream c=new PDPageContentStream(d,page);
    try{c.beginText();c.setFont(PDType1Font.HELVETICA,14);c.newLineAtOffset(72,760);c.showText("Body text "+i+" stays here.");c.endText();
     c.beginText();c.setFont(PDType1Font.HELVETICA,10);c.newLineAtOffset(72,40);c.showText("Company   Confidential");c.endText();
     c.saveGraphicsState();PDExtendedGraphicsState gs=new PDExtendedGraphicsState();gs.setNonStrokingAlphaConstant(0.25f);c.setGraphicsStateParameters(gs);
     c.beginText();c.setFont(PDType1Font.HELVETICA_BOLD,96);c.setTextMatrix(Matrix.getRotateInstance(Math.toRadians(45),150,250));c.showText("DRAFT");c.endText();c.restoreGraphicsState();}
    finally{c.close();}}
   d.save(out);}finally{d.close();}return out;}
}
