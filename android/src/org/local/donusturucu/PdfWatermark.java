package org.local.donusturucu;
import java.io.*;
import java.util.*;
import com.tom_roush.pdfbox.contentstream.PDContentStream;
import com.tom_roush.pdfbox.contentstream.operator.Operator;
import com.tom_roush.pdfbox.cos.*;
import com.tom_roush.pdfbox.pdfparser.PDFStreamParser;
import com.tom_roush.pdfbox.pdfwriter.ContentStreamWriter;
import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle;
import com.tom_roush.pdfbox.pdmodel.common.PDStream;
import com.tom_roush.pdfbox.pdmodel.font.PDFont;
import com.tom_roush.pdfbox.pdmodel.graphics.PDXObject;
import com.tom_roush.pdfbox.pdmodel.graphics.form.PDFormXObject;
import com.tom_roush.pdfbox.pdmodel.graphics.state.PDExtendedGraphicsState;
import com.tom_roush.pdfbox.pdmodel.interactive.annotation.PDAnnotation;

/** Removes watermarks from PDF pages without turning them into pictures.
 *  Automatic: watermark annotations, content marked as a watermark artifact or optional
 *  content layer, and see-through text drawn at an angle. With a word: every text block or
 *  form that contains it. Optionally pictures/forms repeated on most pages. Marked areas are
 *  covered with the colour around them. */
final class PdfWatermark {
 interface Host {void check() throws Exception;
  /** Colour around a marked area (normalized to the page as shown); white when unknown. */
  int surrounding(int page,double[] region) throws Exception;}
 static final class Options {boolean auto=true,repeated=false;String keyword="";List<double[]> regions=new ArrayList<double[]>();}
 static final class Result {File file;int removed;}

 static Result clean(File source,File folder,Options o,Host host)throws Exception{
  PDDocument doc=PDDocument.load(source);Result result=new Result();
  try{
   if(doc.isEncrypted())doc.setAllSecurityToBeRemoved(true);
   String word=normal(o.keyword);Set<COSBase> repeated=o.repeated?repeated(doc):new HashSet<COSBase>();
   Cleaner cleaner=new Cleaner(doc,o.auto,word,repeated,host);int index=0;
   for(PDPage page:doc.getPages()){host.check();
    if(o.auto){List<PDAnnotation> kept=new ArrayList<PDAnnotation>();List<PDAnnotation> all=page.getAnnotations();
     for(PDAnnotation a:all){if("Watermark".equals(a.getSubtype()))cleaner.removed++;else kept.add(a);}
     if(kept.size()!=all.size())page.setAnnotations(kept);}
    cleaner.page(page);
    for(double[] r:o.regions)cover(doc,page,r,host.surrounding(index,r));
    index++;}
   result.removed=cleaner.removed+o.regions.size()*doc.getNumberOfPages();
   result.file=new File(folder,"clean.pdf");doc.save(result.file);
  }finally{doc.close();}
  return result;
 }

 /** Lower case, no spaces: "C O N F I D E N T I A L" and "Confidential" match. */
 static String normal(String s){StringBuilder b=new StringBuilder();for(char c:s.toLowerCase(new Locale("tr")).toCharArray())if(!Character.isWhitespace(c))b.append(c);return b.toString();}

 /** Pictures and forms drawn directly on at least 60 % of the pages (and on two or more). */
 static Set<COSBase> repeated(PDDocument doc)throws Exception{
  Map<COSBase,Set<Integer>> seen=new HashMap<COSBase,Set<Integer>>();int index=0,pages=doc.getNumberOfPages();
  for(PDPage page:doc.getPages()){PDResources res=page.getResources();
   List<Object> tokens=tokens(page);for(int i=1;i<tokens.size();i++){Object t=tokens.get(i);
    if(t instanceof Operator&&((Operator)t).getName().equals("Do")&&tokens.get(i-1) instanceof COSName&&res!=null){
     COSBase target=xobjectBase(res,(COSName)tokens.get(i-1));if(target==null)continue;
     Set<Integer> on=seen.get(target);if(on==null)seen.put(target,on=new HashSet<Integer>());on.add(index);}}
   index++;}
  Set<COSBase> out=new HashSet<COSBase>();int need=Math.max(2,(int)Math.ceil(pages*0.6));
  if(pages>=2)for(Map.Entry<COSBase,Set<Integer>> e:seen.entrySet())if(e.getValue().size()>=need)out.add(e.getKey());
  return out;
 }
 static COSBase xobjectBase(PDResources res,COSName name){COSDictionary x=res.getCOSObject().getCOSDictionary(COSName.XOBJECT);if(x==null)return null;COSBase b=x.getDictionaryObject(name);return b;}
 static List<Object> tokens(PDContentStream stream)throws IOException{PDFStreamParser p=new PDFStreamParser(stream);p.parse();return p.getTokens();}

 private static final class Cleaner{
  final PDDocument doc;final boolean auto;final String word;final Set<COSBase> repeated;final Host host;int removed;final Set<COSBase> visitedForms=new HashSet<COSBase>();
  Cleaner(PDDocument d,boolean a,String w,Set<COSBase> r,Host h){doc=d;auto=a;word=w;repeated=r;host=h;}
  void page(PDPage page)throws Exception{List<Object> in=tokens(page);List<Object> out=filter(in,page.getResources(),0);if(out.size()!=in.size()){PDStream s=new PDStream(doc);write(s.createOutputStream(COSName.FLATE_DECODE),out);page.setContents(s);}}
  static void write(OutputStream os,List<Object> tokens)throws IOException{try{new ContentStreamWriter(os).writeTokens(tokens);}finally{os.close();}}

  /** One graphics state level; Tf, gs and cm are restored by Q. */
  static final class State{COSName font;boolean faint,turned;State copy(){State s=new State();s.font=font;s.faint=faint;s.turned=turned;return s;}}

  List<Object> filter(List<Object> tokens,PDResources res,int depth)throws Exception{
   List<Object> out=new ArrayList<Object>(tokens.size());List<Object> operands=new ArrayList<Object>();
   Deque<Boolean> marked=new ArrayDeque<Boolean>();int hidden=0;Deque<State> states=new ArrayDeque<State>();State st=new State();
   List<Object> block=null;StringBuilder blockText=null;boolean blockTurned=false;
   for(Object t:tokens){
    if(!(t instanceof Operator)){operands.add(t);continue;}
    Operator op=(Operator)t;String name=op.getName();List<Object> unit=new ArrayList<Object>(operands);unit.add(op);operands.clear();
    if(name.equals("BDC")||name.equals("BMC")){boolean drop=auto&&name.equals("BDC")&&watermarkMark(unit,res);marked.push(drop);if(drop){hidden++;removed++;}if(hidden>0)continue;}
    else if(name.equals("EMC")){boolean drop=!marked.isEmpty()&&marked.pop();boolean inside=hidden>0;if(drop)hidden--;if(inside)continue;}
    if(hidden>0)continue;
    if(name.equals("q")){states.push(st.copy());}
    else if(name.equals("Q")){if(!states.isEmpty())st=states.pop();}
    else if(name.equals("cm")&&unit.size()==7){st.turned=st.turned||turned(unit);}
    else if(name.equals("gs")&&unit.size()==2&&unit.get(0) instanceof COSName&&res!=null){PDExtendedGraphicsState g=res.getExtGState((COSName)unit.get(0));if(g!=null){Float a=g.getNonStrokingAlphaConstant();if(a!=null)st.faint=a<0.95f;}}
    else if(name.equals("Tf")&&unit.size()==3&&unit.get(0) instanceof COSName)st.font=(COSName)unit.get(0);
    if(name.equals("BT")){block=new ArrayList<Object>();blockText=new StringBuilder();blockTurned=false;}
    if(block!=null){
     block.addAll(unit);
     if(name.equals("Tm")&&unit.size()==7)blockTurned=blockTurned||turned(unit);
     if(name.equals("Tj")||name.equals("'")||name.equals("\"")||name.equals("TJ"))blockText.append(decode(unit,res,st.font));
     if(name.equals("ET")){
      String text=normal(blockText.toString());boolean drop=(word.length()>0&&text.contains(word))||(auto&&text.length()>0&&(blockTurned||st.turned)&&st.faint);
      if(drop)removed++;else out.addAll(block);block=null;}
     continue;}
    if(name.equals("Do")&&unit.size()==2&&unit.get(0) instanceof COSName&&res!=null&&dropXObject(res,(COSName)unit.get(0),st,depth)){removed++;continue;}
    out.addAll(unit);
   }
   if(block!=null)out.addAll(block);out.addAll(operands);return out;
  }
  /** An angle between 10° and 80° (diagonal "DRAFT" text). */
  static boolean turned(List<Object> unit){float a=num(unit.get(0)),b=num(unit.get(1));double deg=Math.abs(Math.toDegrees(Math.atan2(b,a)))%180;if(deg>90)deg=180-deg;return deg>10&&deg<80;}
  static float num(Object o){return o instanceof COSNumber?((COSNumber)o).floatValue():0;}
  boolean watermarkMark(List<Object> unit,PDResources res){
   Object tag=unit.get(0),props=unit.size()>2?unit.get(1):null;COSDictionary d=null;
   if(props instanceof COSDictionary)d=(COSDictionary)props;
   else if(props instanceof COSName&&res!=null){COSDictionary all=res.getCOSObject().getCOSDictionary(COSName.PROPERTIES);if(all!=null){COSBase b=all.getDictionaryObject((COSName)props);if(b instanceof COSDictionary)d=(COSDictionary)b;}}
   if(tag instanceof COSName&&((COSName)tag).getName().toLowerCase(Locale.ROOT).contains("watermark"))return true;
   if(d==null)return false;
   String subtype=d.getNameAsString(COSName.SUBTYPE),name=d.getString(COSName.NAME);
   if("Watermark".equals(subtype))return true;
   return name!=null&&(name.toLowerCase(Locale.ROOT).contains("watermark")||name.toLowerCase(new Locale("tr")).contains("filigran"));
  }
  boolean dropXObject(PDResources res,COSName name,State st,int depth)throws Exception{
   COSBase base=xobjectBase(res,name);if(base==null)return false;
   if(repeated.contains(base))return true;
   PDXObject x;try{x=res.getXObject(name);}catch(IOException e){return false;}
   if(!(x instanceof PDFormXObject))return false;PDFormXObject form=(PDFormXObject)x;
   COSDictionary oc=form.getCOSObject().getCOSDictionary(COSName.getPDFName("OC"));
   if(auto&&oc!=null){String n=oc.getString(COSName.NAME);if(n!=null&&n.toLowerCase(Locale.ROOT).contains("watermark"))return true;}
   COSDictionary piece=form.getCOSObject().getCOSDictionary(COSName.getPDFName("PieceInfo"));
   if(auto&&piece!=null&&piece.containsKey(COSName.getPDFName("ADBE_CompoundType"))){COSDictionary c=piece.getCOSDictionary(COSName.getPDFName("ADBE_CompoundType"));COSBase priv=c==null?null:c.getDictionaryObject(COSName.getPDFName("Private"));if(priv instanceof COSName&&((COSName)priv).getName().equals("Watermark"))return true;}
   // Forms are shared between pages: clean each once, in place.
   if(depth<4&&visitedForms.add(base)){host.check();List<Object> in=tokens(form);PDResources inner=form.getResources()==null?res:form.getResources();List<Object> out=filter(in,inner,depth+1);
    if(out.isEmpty()&&!in.isEmpty())return true;
    if(out.size()!=in.size())write(form.getCOSObject().createOutputStream(COSName.FLATE_DECODE),out);}
   return false;
  }
  static String decode(List<Object> unit,PDResources res,COSName fontName){
   PDFont font=null;try{if(res!=null&&fontName!=null)font=res.getFont(fontName);}catch(Exception ignored){}
   StringBuilder b=new StringBuilder();for(Object o:unit){
    if(o instanceof COSString)b.append(decode((COSString)o,font));
    else if(o instanceof COSArray)for(COSBase x:(COSArray)o)if(x instanceof COSString)b.append(decode((COSString)x,font));}
   return b.toString();}
  static String decode(COSString s,PDFont font){byte[]bytes=s.getBytes();if(font==null)return s.getString();
   StringBuilder b=new StringBuilder();InputStream in=new ByteArrayInputStream(bytes);
   try{while(in.available()>0){int code=font.readCode(in);String u=font.toUnicode(code);if(u!=null)b.append(u);}}catch(Exception e){return s.getString();}
   return b.toString();}
 }

 /** Paints a marked area; the region is normalized to the page as a viewer shows it. */
 static void cover(PDDocument doc,PDPage page,double[] r,int color)throws IOException{
  PDRectangle box=page.getCropBox();float llx=box.getLowerLeftX(),lly=box.getLowerLeftY(),W=box.getWidth(),H=box.getHeight();int rot=((page.getRotation()%360)+360)%360;
  double x,y,w,h;
  if(rot==90){x=llx+r[1]*W;y=lly+r[0]*H;w=r[3]*W;h=r[2]*H;}
  else if(rot==180){x=llx+(1-r[0]-r[2])*W;y=lly+r[1]*H;w=r[2]*W;h=r[3]*H;}
  else if(rot==270){x=llx+W-(r[1]+r[3])*W;y=lly+H-(r[0]+r[2])*H;w=r[3]*W;h=r[2]*H;}
  else{x=llx+r[0]*W;y=lly+(1-r[1]-r[3])*H;w=r[2]*W;h=r[3]*H;}
  PDPageContentStream c=new PDPageContentStream(doc,page,PDPageContentStream.AppendMode.APPEND,true,true);
  try{c.setNonStrokingColor(((color>>16)&255)/255f,((color>>8)&255)/255f,(color&255)/255f);c.addRect((float)x,(float)y,(float)w,(float)h);c.fill();}finally{c.close();}
 }
}
