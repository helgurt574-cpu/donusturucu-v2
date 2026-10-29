package org.local.donusturucu;
import android.content.Context;
import android.graphics.*;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import com.googlecode.tesseract.android.TessBaseAPI;
import java.io.*;

/** Local OCR; one bounded bitmap at a time, no page-label text is inserted. */
final class OcrEngine {
 interface Host {void check()throws Exception;void progress(int current,int total);}
 private final Context context;private final Host host;private volatile TessBaseAPI active;
 OcrEngine(Context c,Host h){context=c;host=h;}
 void cancel(){TessBaseAPI api=active;if(api!=null)api.stop();}
 private void install()throws Exception {File root=new File(context.getFilesDir(),"ocr/tessdata");root.mkdirs();for(String name:context.getAssets().list("ocr/tessdata")){File dest=new File(root,name);if(dest.isFile()&&dest.length()>0)continue;File temp=new File(root,name+".tmp");InputStream in=context.getAssets().open("ocr/tessdata/"+name);OutputStream out=new FileOutputStream(temp);try{byte[]b=new byte[65536];int n;while((n=in.read(b))!=-1){host.check();out.write(b,0,n);}}finally{in.close();out.close();}if(!temp.renameTo(dest))throw new IOException("OCR data install failed");}}
 String read(File source,String ext,String language)throws Exception {
  if(!java.util.Arrays.asList("tur+eng","eng","tur","kmr","ara","fas").contains(language))throw new IOException("Unsupported OCR language");install();host.check();TessBaseAPI api=new TessBaseAPI();active=api;
  try{if(!api.init(new File(context.getFilesDir(),"ocr").getAbsolutePath(),language,TessBaseAPI.OEM_LSTM_ONLY))throw new IOException("OCR model could not load");api.setPageSegMode(3);StringBuilder text=new StringBuilder();
   if(ext.equals("pdf")){ParcelFileDescriptor fd=ParcelFileDescriptor.open(source,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer pdf=null;try{pdf=new PdfRenderer(fd);for(int n=0;n<pdf.getPageCount();n++){host.check();host.progress(n+1,pdf.getPageCount());PdfRenderer.Page page=pdf.openPage(n);Bitmap bitmap=null;try{float scale=Math.min(3f,2600f/Math.max(page.getWidth(),page.getHeight()));bitmap=Bitmap.createBitmap(Math.max(1,Math.round(page.getWidth()*scale)),Math.max(1,Math.round(page.getHeight()*scale)),Bitmap.Config.ARGB_8888);bitmap.eraseColor(Color.WHITE);page.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_PRINT);String result=recognize(api,bitmap);if(text.length()>0&&result.length()>0)text.append("\n\n");text.append(result);}finally{if(bitmap!=null)bitmap.recycle();page.close();}}}finally{if(pdf!=null)pdf.close();else fd.close();}}
   else{host.progress(1,1);BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeFile(source.getAbsolutePath(),bounds);if(bounds.outWidth<=0)throw new IOException("Image could not load");BitmapFactory.Options options=new BitmapFactory.Options();int sample=1;while(Math.max(bounds.outWidth,bounds.outHeight)/sample>3200)sample*=2;options.inSampleSize=sample;Bitmap image=BitmapFactory.decodeFile(source.getAbsolutePath(),options);if(image==null)throw new IOException("Image could not load");try{Bitmap upright=orient(source,image);if(upright!=image){image.recycle();image=upright;}text.append(recognize(api,image));}finally{image.recycle();}}
   host.check();return text.toString().trim();
  }finally{active=null;api.recycle();}
 }
 // BitmapFactory ignores JPEG EXIF rotation/mirroring. Normalize before OCR.
 private Bitmap orient(File source,Bitmap image){
  int value=1;try{value=new android.media.ExifInterface(source.getAbsolutePath()).getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION,1);}catch(IOException ignored){return image;}
  Matrix matrix=new Matrix();switch(value){
   case 2:matrix.setScale(-1,1);break;
   case 3:matrix.setRotate(180);break;
   case 4:matrix.setRotate(180);matrix.postScale(-1,1);break;
   case 5:matrix.setRotate(90);matrix.postScale(-1,1);break;
   case 6:matrix.setRotate(90);break;
   case 7:matrix.setRotate(-90);matrix.postScale(-1,1);break;
   case 8:matrix.setRotate(-90);break;
   default:return image;
  }return Bitmap.createBitmap(image,0,0,image.getWidth(),image.getHeight(),matrix,true);
 }
 private String recognize(TessBaseAPI api,Bitmap image)throws Exception {host.check();api.setImage(image);String text=api.getUTF8Text();host.check();api.clear();return text==null?"":text.trim();}
}
