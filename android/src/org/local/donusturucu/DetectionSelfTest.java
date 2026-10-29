package org.local.donusturucu;
import java.io.*;import java.util.*;import java.util.zip.*;import java.security.*;import android.graphics.*;import org.json.*;
/** Device tests use the same classifier and native probe as the file picker. */
final class DetectionSelfTest {
 static void bytes(File f,byte[] b)throws Exception{FileOutputStream out=new FileOutputStream(f);try{out.write(b);}finally{out.close();}}
 static String hash(File f)throws Exception{MessageDigest d=MessageDigest.getInstance("SHA-256");InputStream in=new FileInputStream(f);try{byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)d.update(b,0,n);}finally{in.close();}return Arrays.toString(d.digest());}
 static void odf(File f,String mime)throws Exception{ZipOutputStream z=new ZipOutputStream(new FileOutputStream(f));try{z.putNextEntry(new ZipEntry("mimetype"));z.write(mime.getBytes("US-ASCII"));z.closeEntry();z.putNextEntry(new ZipEntry("content.xml"));z.write(("<?xml version=\"1.0\"?><office:document-content xmlns:office=\"urn:oasis:names:tc:opendocument:xmlns:office:1.0\" xmlns:text=\"urn:oasis:names:tc:opendocument:xmlns:text:1.0\"><office:body><office:presentation><text:p>Silav Merhaba</text:p></office:presentation></office:body></office:document-content>").getBytes("UTF-8"));z.closeEntry();}finally{z.close();}}
 static void run(MainActivity a)throws Exception{
  File root=new File(a.getExternalFilesDir(null),"detection-test");root.mkdirs();JSONArray rows=new JSONArray();
  String[][] cases={{"png-as-mp4","mp4","image"},{"jpeg-as-docx","docx","image"},{"webp-no-extension","bin","image"},{"gif-as-txt","txt","gif"},{"gif","gif","gif"},{"odp-as-zip","zip","odp"},{"odt-as-pptx","pptx","odt"},{"utf8-no-extension","bin","txt"},{"utf16-as-mp3","mp3","txt"},{"pdf-as-mp4","mp4","pdf"},{"docx-as-bin","bin","docx"},{"pptx-as-bin","bin","pptx"},{"broken-zip","zip","error"},{"unsupported-ods","ods","error"},{"broken-pdf","pdf","pdf-error"}};
  for(int repeat=1;repeat<=3;repeat++)for(String[] test:cases){JSONObject row=new JSONObject();row.put("case",test[0]);row.put("repeat",repeat);File f=new File(root,test[0]+"-"+repeat+"."+test[1]);try{
   if(test[2].equals("image")){Bitmap bmp=Bitmap.createBitmap(80,60,Bitmap.Config.ARGB_8888);bmp.eraseColor(Color.GREEN);FileOutputStream out=new FileOutputStream(f);try{bmp.compress(test[0].startsWith("png")?Bitmap.CompressFormat.PNG:test[0].startsWith("jpeg")?Bitmap.CompressFormat.JPEG:Bitmap.CompressFormat.WEBP,95,out);}finally{out.close();bmp.recycle();}}
   else if(test[2].equals("gif"))AndroidSelfTest.copy(a,"detection-animated.gif",f);
   else if(test[0].startsWith("odp")||test[0].startsWith("odt")||test[0].equals("unsupported-ods"))odf(f,"application/vnd.oasis.opendocument."+(test[0].startsWith("odp")?"presentation":test[0].startsWith("odt")?"text":"spreadsheet"));
   else if(test[0].startsWith("utf"))bytes(f,"Merhaba Silav مرحبا سلام".getBytes(test[0].startsWith("utf16")?"UTF-16":"UTF-8"));
   else if(test[0].equals("pptx-as-bin"))AndroidSelfTest.copy(a,"rich.pptx",f);
   else if(test[0].equals("broken-zip"))bytes(f,new byte[]{80,75,3,4,0,0});
   else if(test[0].equals("broken-pdf"))bytes(f,"%PDF-1.7\nbroken".getBytes("US-ASCII"));
   else {String format=test[0].split("-")[0];File exported=DocumentEngine.write("Merhaba Silav",format,root);FileInputStream in=new FileInputStream(exported);ByteArrayOutputStream b=new ByteArrayOutputStream();try{byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1)b.write(buf,0,n);}finally{in.close();}bytes(f,b.toByteArray());}
   String before=hash(f),actual="";boolean rejected=false;try{actual=a.detectDocument(f,test[1]);}catch(IOException expected){rejected=true;}
   if(test[2].equals("error")){if(!rejected)throw new IOException("Malformed/unsupported file accepted: "+actual);}
   else {if(rejected||!actual.equals(test[2].equals("pdf-error")?"pdf":test[2]))throw new IOException("Wrong detection: "+actual);
    if(actual.equals("gif")){MediaEngine.Info media=a.probe(f);if(!media.video||Math.abs(media.duration-1)>0.15)throw new IOException("GIF animation lost");File output=new File(root,"gif-"+test[0]+"-"+repeat+".mp4");a.execute(new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",f.getAbsolutePath(),"-c:v","libx264","-pix_fmt","yuv420p","-y",output.getAbsolutePath())));MediaEngine.Info back=a.probe(output);if(!back.video||Math.abs(back.duration-1)>0.15)throw new IOException("Bad GIF conversion duration");
     for(int frame=0;frame<2;frame++){File still=new File(root,"frame-"+test[0]+"-"+repeat+"-"+frame+".png");a.execute(new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",output.getAbsolutePath(),"-vf","trim=start_frame="+frame+":end_frame="+(frame+1)+",setpts=PTS-STARTPTS","-frames:v","1","-y",still.getAbsolutePath())));Bitmap pic=BitmapFactory.decodeFile(still.getAbsolutePath());if(pic==null)throw new IOException("Frame missing");int color=pic.getPixel(80,60);pic.recycle();if(frame==0?Color.red(color)<200||Color.blue(color)>30:Color.blue(color)<200||Color.red(color)>30)throw new IOException("Animation frame content lost");}}
    if(test[2].equals("pdf-error")){boolean bad=false;try{DocumentEngine.read(f,"pdf");}catch(Exception expected){bad=true;}if(!bad)throw new IOException("Broken PDF was accepted");}
    if(actual.equals("odp")&&!DocumentEngine.read(f,actual).contains("Silav"))throw new IOException("Presentation text lost");
   }
   if(!before.equals(hash(f)))throw new IOException("Original changed");row.put("detected",actual);row.put("source_unchanged",true);row.put("pass",true);
  }catch(Exception e){row.put("pass",false);row.put("error",e.toString());}rows.put(row);FeatureSelfTest.write(root,rows);}
  a.message("Detection tests complete: "+rows.length());
 }
}
