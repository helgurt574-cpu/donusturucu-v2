package org.local.donusturucu;
import android.graphics.*;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import java.io.*;
import java.util.*;
import com.tom_roush.pdfbox.cos.COSName;
import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.pdmodel.graphics.PDXObject;
import com.tom_roush.pdfbox.pdmodel.graphics.form.PDFormXObject;
import com.tom_roush.pdfbox.pdmodel.graphics.image.JPEGFactory;
import com.tom_roush.pdfbox.pdmodel.graphics.image.PDImageXObject;

/** Picture and PDF page tools that run on Android's own graphics, PdfRenderer and PDFBox. */
final class Tools {
 interface Host {void check() throws Exception;}
 static final List<String> IMAGE_OUT=Arrays.asList("jpg","png","webp","bmp","pdf");

 /** Format a picture keeps after an edit: JPG stays JPG, WEBP stays WEBP, everything else PNG. */
 static String keptImageExt(String name){String e=name.contains(".")?name.substring(name.lastIndexOf('.')+1).toLowerCase(Locale.ROOT):"";
  if(e.equals("jpg")||e.equals("jpeg")||e.equals("jfif"))return "jpg";if(e.equals("webp"))return "webp";return "png";}

 /** Decoded upright (EXIF rotation applied), at most maxSide pixels on the long side. */
 static Bitmap load(File f,int maxSide)throws IOException{
  BitmapFactory.Options o=new BitmapFactory.Options();o.inJustDecodeBounds=true;BitmapFactory.decodeFile(f.getAbsolutePath(),o);
  if(o.outWidth<=0||o.outHeight<=0)throw new IOException("Unreadable picture");
  int sample=1;while(Math.max(o.outWidth,o.outHeight)/sample>maxSide)sample*=2;
  BitmapFactory.Options d=new BitmapFactory.Options();d.inSampleSize=sample;d.inPreferredConfig=Bitmap.Config.ARGB_8888;Bitmap b=BitmapFactory.decodeFile(f.getAbsolutePath(),d);
  if(b==null)throw new IOException("Unreadable picture");
  int turn=0;boolean mirror=false;
  try{android.media.ExifInterface exif=new android.media.ExifInterface(f.getAbsolutePath());int or=exif.getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION,1);
   turn=or==6||or==7?90:or==3||or==4?180:or==8||or==5?270:0;mirror=or==2||or==4||or==5||or==7;}catch(Exception ignored){}
  if(turn==0&&!mirror)return b;
  Matrix m=new Matrix();if(mirror)m.postScale(-1,1);m.postRotate(turn);Bitmap r=Bitmap.createBitmap(b,0,0,b.getWidth(),b.getHeight(),m,true);if(r!=b)b.recycle();return r;
 }

 static File save(Bitmap b,String fmt,int quality,File out)throws IOException{
  if(fmt.equals("pdf")){android.graphics.pdf.PdfDocument doc=new android.graphics.pdf.PdfDocument();try{addPage(doc,b,1);FileOutputStream o=new FileOutputStream(out);try{doc.writeTo(o);}finally{o.close();}}finally{doc.close();}return out;}
  if(fmt.equals("bmp")){writeBmp(b,out);return out;}
  Bitmap.CompressFormat cf;Bitmap src=b;
  if(fmt.equals("jpg")){cf=Bitmap.CompressFormat.JPEG;if(b.hasAlpha())src=flatten(b);}
  else if(fmt.equals("webp"))cf=android.os.Build.VERSION.SDK_INT>=30?Bitmap.CompressFormat.WEBP_LOSSY:Bitmap.CompressFormat.WEBP;
  else cf=Bitmap.CompressFormat.PNG;
  FileOutputStream o=new FileOutputStream(out);try{if(!src.compress(cf,quality,o))throw new IOException("Cannot write picture");}finally{o.close();if(src!=b)src.recycle();}
  return out;
 }
 /** Transparent parts become white before JPEG/BMP, which have no transparency. */
 static Bitmap flatten(Bitmap b){Bitmap w=Bitmap.createBitmap(b.getWidth(),b.getHeight(),Bitmap.Config.ARGB_8888);w.eraseColor(Color.WHITE);new Canvas(w).drawBitmap(b,0,0,null);return w;}
 static void writeBmp(Bitmap b,File out)throws IOException{
  Bitmap s=b.hasAlpha()?flatten(b):b;int w=s.getWidth(),h=s.getHeight(),row=(w*3+3)/4*4,size=54+row*h;int[] px=new int[w];
  OutputStream o=new BufferedOutputStream(new FileOutputStream(out));
  try{byte[] head=new byte[54];head[0]='B';head[1]='M';le(head,2,size);le(head,10,54);le(head,14,40);le(head,18,w);le(head,22,h);head[26]=1;head[28]=24;le(head,34,row*h);le(head,38,2835);le(head,42,2835);o.write(head);
   byte[] line=new byte[row];for(int y=h-1;y>=0;y--){s.getPixels(px,0,w,0,y,w,1);for(int x=0;x<w;x++){line[x*3]=(byte)(px[x]&255);line[x*3+1]=(byte)((px[x]>>8)&255);line[x*3+2]=(byte)((px[x]>>16)&255);}o.write(line);}}
  finally{o.close();if(s!=b)s.recycle();}
 }
 private static void le(byte[] b,int at,int v){b[at]=(byte)v;b[at+1]=(byte)(v>>8);b[at+2]=(byte)(v>>16);b[at+3]=(byte)(v>>24);}
 /** A page as wide as A4 (595 pt) holding the whole picture. */
 static void addPage(android.graphics.pdf.PdfDocument doc,Bitmap b,int number){
  int pw=595,ph=Math.max(1,Math.min(14400,Math.round(595f*b.getHeight()/b.getWidth())));
  android.graphics.pdf.PdfDocument.Page page=doc.startPage(new android.graphics.pdf.PdfDocument.PageInfo.Builder(pw,ph,number).create());
  Paint p=new Paint(Paint.FILTER_BITMAP_FLAG);page.getCanvas().drawBitmap(b,null,new RectF(0,0,pw,ph),p);doc.finishPage(page);
 }
 static int quality(String level){return level.equals("1")?95:level.equals("3")?70:85;}

 /** Picture → JPG/PNG/WEBP/BMP/PDF with optional size, grey and rotation changes. */
 static File convertImage(File src,String fmt,Map<String,String> o,File work)throws IOException{
  Bitmap b=edit(load(src,6000),o);try{return save(b,fmt,quality(get(o,"q","2")),new File(work,"picture."+fmt));}finally{b.recycle();}
 }
 static String get(Map<String,String> o,String k,String d){String v=o.get(k);return v==null||v.length()==0?d:v;}
 /** scale (percent), angle (90/180/270), flip (1) and gray (1). */
 static Bitmap edit(Bitmap b,Map<String,String> o){
  int scale=Integer.parseInt(get(o,"scale","100")),angle=Integer.parseInt(get(o,"angle","0"));boolean flip=get(o,"flip","0").equals("1"),gray=get(o,"gray","0").equals("1");
  if(scale!=100||angle!=0||flip){Matrix m=new Matrix();float f=Math.max(1,Math.min(400,scale))/100f;m.postScale(flip?-f:f,f);m.postRotate(angle);
   Bitmap r=Bitmap.createBitmap(b,0,0,b.getWidth(),b.getHeight(),m,true);if(r!=b){b.recycle();b=r;}}
  if(gray){Bitmap g=Bitmap.createBitmap(b.getWidth(),b.getHeight(),Bitmap.Config.ARGB_8888);ColorMatrix cm=new ColorMatrix();cm.setSaturation(0);Paint p=new Paint();p.setColorFilter(new ColorMatrixColorFilter(cm));new Canvas(g).drawBitmap(b,0,0,p);b.recycle();b=g;}
  return b;
 }
 /** Upright PNG copy so that ffmpeg and the preview see the same pixels. */
 static File upright(File src,File work)throws IOException{Bitmap b=load(src,6000);try{return save(b,"png",100,new File(work,"upright.png"));}finally{b.recycle();}}
 static File imagesToPdf(List<File> pictures,File work,Host host)throws Exception{
  android.graphics.pdf.PdfDocument doc=new android.graphics.pdf.PdfDocument();File out=new File(work,"pictures.pdf");
  try{int n=1;for(File f:pictures){host.check();Bitmap b=load(f,3000);try{addPage(doc,b,n++);}finally{b.recycle();}}FileOutputStream o=new FileOutputStream(out);try{doc.writeTo(o);}finally{o.close();}}finally{doc.close();}
  return out;
 }

 // ---- PDF pages
 static int pageCount(File pdf){try{ParcelFileDescriptor fd=ParcelFileDescriptor.open(pdf,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer r=new PdfRenderer(fd);try{return r.getPageCount();}finally{r.close();}}catch(Exception e){return MainActivity.pdfPages(pdf);}}
 /** One page as shown by a viewer (rotation applied), width pixels wide, on white. */
 static Bitmap renderPage(File pdf,int index,int width)throws IOException{
  try{ParcelFileDescriptor fd=ParcelFileDescriptor.open(pdf,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer r=new PdfRenderer(fd);
   try{PdfRenderer.Page p=r.openPage(Math.max(0,Math.min(index,r.getPageCount()-1)));try{int w=Math.max(16,width),h=Math.max(16,Math.round((float)w*p.getHeight()/p.getWidth()));if((long)w*h>24_000_000L){h=Math.min(h,6000);}
    Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);b.eraseColor(Color.WHITE);p.render(b,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);return b;}finally{p.close();}}finally{r.close();}}
  catch(Exception androidFailed){
   // Encrypted or unusual files: PDFBox draws them instead.
   PDDocument d=PDDocument.load(pdf);try{com.tom_roush.pdfbox.rendering.PDFRenderer r=new com.tom_roush.pdfbox.rendering.PDFRenderer(d);PDPage page=d.getPage(Math.max(0,Math.min(index,d.getNumberOfPages()-1)));
    float pw=(page.getRotation()%180==0?page.getCropBox().getWidth():page.getCropBox().getHeight());Bitmap b=r.renderImage(Math.max(0,Math.min(index,d.getNumberOfPages()-1)),width/Math.max(1f,pw));return b;}finally{d.close();}}
 }
 static List<File> pdfToImages(File pdf,String fmt,int dpi,File work,Host host)throws Exception{
  int n=pageCount(pdf);List<File> out=new ArrayList<File>();
  for(int i=0;i<n;i++){host.check();float pts=pageWidth(pdf,i);int w=Math.max(64,Math.min(5000,Math.round(pts*dpi/72f)));Bitmap b=renderPage(pdf,i,w);
   try{out.add(save(b,fmt,92,new File(work,String.format(Locale.ROOT,"page-%03d.%s",i+1,fmt))));}finally{b.recycle();}}
  if(out.isEmpty())throw new IOException("Empty PDF");return out;
 }
 static float pageWidth(File pdf,int index){try{ParcelFileDescriptor fd=ParcelFileDescriptor.open(pdf,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer r=new PdfRenderer(fd);try{PdfRenderer.Page p=r.openPage(index);try{return p.getWidth();}finally{p.close();}}finally{r.close();}}catch(Exception e){return 595;}}

 /** "1-3, 5, 8-" → zero-based page numbers in the written order. */
 static List<Integer> parsePages(String spec,int count){List<Integer> out=new ArrayList<Integer>();
  for(String part:spec.replace(' ',',').split("[,;]+")){part=part.trim();if(part.length()==0)continue;
   int dash=part.indexOf('-');int a,b;
   if(dash<0){a=b=Integer.parseInt(part);}else{String l=part.substring(0,dash).trim(),r=part.substring(dash+1).trim();a=l.length()==0?1:Integer.parseInt(l);b=r.length()==0?count:Integer.parseInt(r);}
   if(a<1||b<1||a>count||b>count)throw new IllegalArgumentException("page_range");
   if(a<=b)for(int i=a;i<=b;i++)out.add(i-1);else for(int i=a;i>=b;i--)out.add(i-1);}
  if(out.isEmpty())throw new IllegalArgumentException("page_range");return out;}

 /** Keep (in the given order) or delete the listed pages. */
 static File pdfPages(File src,String spec,boolean keep,File work)throws Exception{
  PDDocument doc=PDDocument.load(src);try{if(doc.isEncrypted())doc.setAllSecurityToBeRemoved(true);int n=doc.getNumberOfPages();List<Integer> list=parsePages(spec,n);
   PDDocument out=new PDDocument();try{
    if(keep){for(int i:list)out.importPage(doc.getPage(i));}
    else{Set<Integer> drop=new HashSet<Integer>(list);if(drop.size()>=n)throw new IllegalArgumentException("page_range");for(int i=0;i<n;i++)if(!drop.contains(i))out.importPage(doc.getPage(i));}
    File f=new File(work,"pages.pdf");out.save(f);return f;}finally{out.close();}}finally{doc.close();}
 }
 static File pdfRotate(File src,int angle,String spec,File work)throws Exception{
  PDDocument doc=PDDocument.load(src);try{if(doc.isEncrypted())doc.setAllSecurityToBeRemoved(true);int n=doc.getNumberOfPages();
   Collection<Integer> pages=spec==null||spec.trim().length()==0?null:new HashSet<Integer>(parsePages(spec,n));
   for(int i=0;i<n;i++)if(pages==null||pages.contains(i)){PDPage p=doc.getPage(i);p.setRotation(((p.getRotation()+angle)%360+360)%360);}
   File f=new File(work,"rotated.pdf");doc.save(f);return f;}finally{doc.close();}
 }
 /** Recompresses large pictures inside the PDF as JPEG; the text stays text. */
 static File pdfCompress(File src,int level,File work,Host host)throws Exception{
  int maxSide=level==1?2400:level==3?1100:1600;float q=level==1?0.82f:level==3?0.5f:0.68f;
  PDDocument doc=PDDocument.load(src);File f=new File(work,"compressed.pdf");
  try{if(doc.isEncrypted())doc.setAllSecurityToBeRemoved(true);Set<Object> done=new HashSet<Object>();
   for(PDPage page:doc.getPages()){host.check();shrink(doc,page.getResources(),maxSide,q,done,host,0);}
   doc.save(f);}finally{doc.close();}
  if(f.length()>=src.length()){copy(src,f);}
  return f;
 }
 private static void shrink(PDDocument doc,PDResources res,int maxSide,float q,Set<Object> done,Host host,int depth)throws Exception{
  if(res==null||depth>4)return;
  for(COSName name:res.getXObjectNames()){host.check();PDXObject x;try{x=res.getXObject(name);}catch(IOException e){continue;}
   if(x==null||!done.add(x.getCOSObject()))continue;
   if(x instanceof PDFormXObject){shrink(doc,((PDFormXObject)x).getResources(),maxSide,q,done,host,depth+1);continue;}
   if(!(x instanceof PDImageXObject))continue;PDImageXObject img=(PDImageXObject)x;
   if(img.isStencil()||img.getBitsPerComponent()==1||img.getCOSObject().containsKey(COSName.SMASK)||img.getCOSObject().containsKey(COSName.MASK))continue;
   long before=img.getCOSObject().getLength();if(before<60_000)continue;
   Bitmap b;try{b=img.getImage();}catch(Exception e){continue;}if(b==null)continue;
   try{int w=b.getWidth(),h=b.getHeight();float s=Math.min(1f,(float)maxSide/Math.max(w,h));Bitmap small=s<1?Bitmap.createScaledBitmap(b,Math.max(1,Math.round(w*s)),Math.max(1,Math.round(h*s)),true):b;
    try{PDImageXObject jpeg=JPEGFactory.createFromImage(doc,small.hasAlpha()?flatten(small):small,q);if(jpeg.getCOSObject().getLength()<before*0.9)res.put(name,jpeg);}finally{if(small!=b)small.recycle();}}
   finally{b.recycle();}}
 }
 static void copy(File from,File to)throws IOException{InputStream in=new FileInputStream(from);try{OutputStream o=new FileOutputStream(to);try{byte[]b=new byte[65536];int n;while((n=in.read(b))>0)o.write(b,0,n);}finally{o.close();}}finally{in.close();}}

 /** Typical colour just outside a marked area of a page (median of a thin ring). */
 static int surrounding(File pdf,int page,double[] r){
  try{Bitmap b=renderPage(pdf,page,700);try{return ring(b,r);}finally{b.recycle();}}catch(Exception e){return Color.WHITE;}
 }
 static int ring(Bitmap b,double[] r){int W=b.getWidth(),H=b.getHeight();int x0=(int)(r[0]*W)-3,y0=(int)(r[1]*H)-3,x1=(int)((r[0]+r[2])*W)+3,y1=(int)((r[1]+r[3])*H)+3;
  List<Integer> rs=new ArrayList<Integer>(),gs=new ArrayList<Integer>(),bs=new ArrayList<Integer>();
  for(int x=x0;x<=x1;x++)for(int y:new int[]{y0,y1})add(b,x,y,rs,gs,bs);for(int y=y0;y<=y1;y++)for(int x:new int[]{x0,x1})add(b,x,y,rs,gs,bs);
  if(rs.isEmpty())return Color.WHITE;Collections.sort(rs);Collections.sort(gs);Collections.sort(bs);int m=rs.size()/2;return Color.rgb(rs.get(m),gs.get(m),bs.get(m));}
 private static void add(Bitmap b,int x,int y,List<Integer> r,List<Integer> g,List<Integer> bl){if(x<0||y<0||x>=b.getWidth()||y>=b.getHeight())return;int c=b.getPixel(x,y);r.add(Color.red(c));g.add(Color.green(c));bl.add(Color.blue(c));}
}
