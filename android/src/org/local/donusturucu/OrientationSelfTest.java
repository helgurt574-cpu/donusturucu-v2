package org.local.donusturucu;
import java.io.*;import java.util.*;import java.security.*;import org.json.*;
final class OrientationSelfTest {
 static void run(final MainActivity a)throws Exception{
  File root=new File(a.getExternalFilesDir(null),"orientation-test");root.mkdirs();JSONArray rows=new JSONArray();
  for(int repeat=1;repeat<=3;repeat++)for(String lang:new String[]{"eng","tur","kmr","ara","fas"})for(String kind:new String[]{"upright","exif2","exif3","exif4","exif5","exif6","exif7","exif8"}){
   JSONObject row=new JSONObject();row.put("language",lang);row.put("kind",kind);row.put("repeat",repeat);
   try{File f=new File(root,lang+"-"+kind+".jpg");AndroidSelfTest.copy(a,"orientation/"+f.getName(),f);String before=DetectionSelfTest.hash(f);String text=new OcrEngine(a,new OcrEngine.Host(){public void check(){}public void progress(int n,int total){a.message("OCR orientation test");}}).read(f,"image",lang);row.put("text",text);String expected=lang.equals("ara")?"مرحبا":lang.equals("fas")?"سلام":lang.equals("kmr")?"Silav":lang.equals("tur")?"Merhaba":"Offline";if(!text.toLowerCase(Locale.ROOT).contains(expected.toLowerCase(Locale.ROOT)))throw new IOException("Expected word missing: "+expected);if(!before.equals(DetectionSelfTest.hash(f)))throw new IOException("Original changed");row.put("source_unchanged",true);row.put("pass",true);
   }catch(Exception e){row.put("pass",false);row.put("error",e.toString());}rows.put(row);FeatureSelfTest.write(root,rows);
  }a.message("Orientation tests complete: "+rows.length());
 }
}
