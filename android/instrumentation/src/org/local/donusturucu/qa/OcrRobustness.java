package org.local.donusturucu.qa;
import android.app.Instrumentation;import android.os.Bundle;import android.content.Context;import java.io.*;import java.lang.reflect.*;import java.security.*;import java.util.*;import org.json.*;
/** Separate signed diagnostic APK invokes the installed release, never replaces it. */
public class OcrRobustness extends Instrumentation {
 public void onCreate(Bundle b){super.onCreate(b);start();}
 String hash(File f)throws Exception{MessageDigest d=MessageDigest.getInstance("SHA-256");InputStream in=new FileInputStream(f);try{byte[]buf=new byte[8192];int n;while((n=in.read(buf))!=-1)d.update(buf,0,n);}finally{in.close();}return Arrays.toString(d.digest());}
 String norm(String s){return s.trim().replaceAll("\\s+"," ").toLowerCase(Locale.ROOT);}
 int distance(String a,String b){int[] prev=new int[b.length()+1];for(int j=0;j<prev.length;j++)prev[j]=j;for(int i=1;i<=a.length();i++){int[]cur=new int[b.length()+1];cur[0]=i;for(int j=1;j<cur.length;j++)cur[j]=Math.min(Math.min(cur[j-1]+1,prev[j]+1),prev[j-1]+(a.charAt(i-1)==b.charAt(j-1)?0:1));prev=cur;}return prev[b.length()];}
 public void onStart(){Bundle result=new Bundle();try{
  Context target=getTargetContext();ClassLoader loader=target.getClassLoader();Class<?> engine=Class.forName("org.local.donusturucu.OcrEngine",true,loader),host=Class.forName("org.local.donusturucu.OcrEngine$Host",true,loader);
  Constructor<?> construct=engine.getDeclaredConstructor(Context.class,host);construct.setAccessible(true);Method read=engine.getDeclaredMethod("read",File.class,String.class,String.class);read.setAccessible(true);
  Object callback=Proxy.newProxyInstance(loader,new Class<?>[]{host},new InvocationHandler(){public Object invoke(Object proxy,Method method,Object[]args){return null;}});
  String[] langs={"eng","tur","kmr","ara","fas"},expected={"OFFLINE OCR TEST","Merhaba dünya. Türkçe belge dönüştürme.","Silav cîhan. Ev belgeya Kurmancî ye.","مرحبا بالعالم","سلام دنیا"};JSONArray rows=new JSONArray();File root=new File(target.getExternalFilesDir(null),"ocr-robustness");root.mkdirs();
  for(int repeat=1;repeat<=3;repeat++)for(int li=0;li<langs.length;li++)for(String kind:new String[]{"plain","contrast","skew"}){JSONObject row=new JSONObject();row.put("language",langs[li]);row.put("kind",kind);row.put("repeat",repeat);try{
   String name=langs[li]+"-"+kind+".png";File f=new File(root,name);InputStream in=getContext().getAssets().open(name);OutputStream out=new FileOutputStream(f);try{byte[]buf=new byte[8192];int n;while((n=in.read(buf))!=-1)out.write(buf,0,n);}finally{in.close();out.close();}String before=hash(f);long begin=System.nanoTime();String text=(String)read.invoke(construct.newInstance(target,callback),f,"image",langs[li]);double cer=distance(norm(expected[li]),norm(text))/(double)norm(expected[li]).length();row.put("text",text);row.put("expected",expected[li]);row.put("cer",cer);row.put("seconds",(System.nanoTime()-begin)/1e9);row.put("source_unchanged",before.equals(hash(f)));row.put("pass",cer<=.15&&before.equals(hash(f)));
  }catch(Throwable e){row.put("pass",false);row.put("error",e.toString());}rows.put(row);JSONObject report=new JSONObject();report.put("release","1.1.2 installed APK");report.put("environment","Android 9 x86_64 emulator");report.put("cases",rows.length());int failures=0;for(int i=0;i<rows.length();i++)if(!rows.getJSONObject(i).getBoolean("pass"))failures++;report.put("failures",failures);report.put("rows",rows);Writer w=new OutputStreamWriter(new FileOutputStream(new File(root,"report.json")),"UTF-8");try{w.write(report.toString(2));}finally{w.close();}}
  result.putString("report",new File(root,"report.json").toString());finish(0,result);
 }catch(Throwable e){result.putString("error",e.toString());finish(1,result);}}
}
