package org.local.donusturucu;
import java.io.*;
import java.nio.charset.Charset;
import java.util.*;
import java.util.zip.*;
import org.xmlpull.v1.*;
import android.text.*;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.text.PDFTextStripper;

/** Text-oriented document conversion; PDF page editing preserves original PDF pages. */
public final class DocumentEngine {
 public static File mergeMany(List<File>files,File folder,RichDocument.Host host)throws Exception{if(files.size()<2)throw new IOException("Choose two PDFs");PDDocument target=new PDDocument();try{for(File file:files){host.check();PDDocument source=PDDocument.load(file);try{new com.tom_roush.pdfbox.multipdf.PDFMergerUtility().appendDocument(target,source);host.check();}finally{source.close();}}File out=new File(folder,"merged.pdf");target.save(out);return out;}finally{target.close();}}
 public static String read(File file,String ext)throws Exception {
  if(ext.equals("pdf")){PDDocument doc=PDDocument.load(file);try{String original=logicalText(doc);return original!=null?original:new PDFTextStripper().getText(doc);}finally{doc.close();}}
  if(Arrays.asList("docx","odt","odp","pptx","xlsx","epub").contains(ext)){
   ZipFile zip=new ZipFile(file);try{
    List<String> entries=new ArrayList<String>();Enumeration<? extends ZipEntry> all=zip.entries();
    while(all.hasMoreElements()){
     String name=all.nextElement().getName();
     if(name.equals("word/document.xml")||name.equals("content.xml")||name.matches("ppt/slides/slide[0-9]+\\.xml")||name.matches("xl/(sharedStrings|worksheets/sheet[0-9]+)\\.xml")||(ext.equals("epub")&&name.matches("(?i).*\\.(xhtml|html|htm)")))entries.add(name);
    }
    if(ext.equals("epub"))entries=epubOrder(zip,entries);else Collections.sort(entries,new Comparator<String>(){public int compare(String a,String b){return natural(a).compareTo(natural(b));}});
    StringBuilder result=new StringBuilder();
    for(String name:entries){InputStream input=zip.getInputStream(zip.getEntry(name));String xml=text(input);input.close();result.append(ext.equals("epub")?Html.fromHtml(xml.replaceAll("(?is)<head.*?</head>", "")).toString().replace("\uFFFC", ""):xmlText(xml)).append('\n');}
    return result.toString().trim();
   }finally{zip.close();}
  }
  FileInputStream stream=new FileInputStream(file);String value;try{value=text(stream);}finally{stream.close();}
  if(ext.equals("html")||ext.equals("htm"))return Html.fromHtml(value).toString().replace("\uFFFC", "");
  if(ext.equals("rtf"))return rtfText(value);
  if(!Arrays.asList("txt","md","csv","tsv","rst").contains(ext))throw new IOException("Unsupported document input");return value;
 }
 private static String natural(String s){java.util.regex.Matcher m=java.util.regex.Pattern.compile("[0-9]+").matcher(s);StringBuffer b=new StringBuffer();while(m.find())m.appendReplacement(b,String.format(Locale.ROOT,"%09d",Integer.parseInt(m.group())));m.appendTail(b);return b.toString();}
 private static String text(InputStream input)throws Exception {ByteArrayOutputStream out=new ByteArrayOutputStream();byte[]b=new byte[8192];int n;while((n=input.read(b))!=-1){if(out.size()>32*1024*1024)throw new IOException("Document text is too large");out.write(b,0,n);}byte[]bytes=out.toByteArray();if(bytes.length>=2&&(bytes[0]&255)==255&&(bytes[1]&255)==254)return new String(bytes,"UTF-16LE").replace("\uFEFF","");if(bytes.length>=2&&(bytes[0]&255)==254&&(bytes[1]&255)==255)return new String(bytes,"UTF-16BE").replace("\uFEFF","");return new String(bytes,"UTF-8").replace("\uFEFF","");}
 private static String xmlText(String xml)throws Exception {
  XmlPullParserFactory f=XmlPullParserFactory.newInstance();f.setNamespaceAware(true);XmlPullParser p=f.newPullParser();p.setInput(new StringReader(xml));StringBuilder out=new StringBuilder();int e;
  while((e=p.next())!=XmlPullParser.END_DOCUMENT){String name=p.getName();if(e==XmlPullParser.TEXT)out.append(p.getText());else if(e==XmlPullParser.END_TAG&&(name.equals("p")||name.equals("h")||name.equals("tr")||name.equals("div")))out.append('\n');else if(e==XmlPullParser.START_TAG&&(name.equals("tab")||name.equals("br")))out.append(name.equals("br")?'\n':'\t');}
  return out.toString();
 }
 private static String rtfText(String value){
  StringBuilder out=new StringBuilder();Stack<Boolean> groups=new Stack<Boolean>();boolean skip=false;int fallback=0,uc=1;
  for(int i=0;i<value.length();){char c=value.charAt(i++);
   if(c=='{'){groups.push(skip);continue;}if(c=='}'){if(!groups.empty())skip=groups.pop();continue;}
   if(c!='\\'){if(c!='\r'&&c!='\n'){if(fallback>0)fallback--;else if(!skip)out.append(c);}continue;}
   if(i>=value.length())break;char next=value.charAt(i++);
   if(next=='\\'||next=='{'||next=='}'){if(fallback>0)fallback--;else if(!skip)out.append(next);continue;}
   if(next=='\''){if(i+2<=value.length()){try{char decoded=new String(new byte[]{(byte)Integer.parseInt(value.substring(i,i+2),16)},java.nio.charset.Charset.forName("windows-1252")).charAt(0);if(fallback>0)fallback--;else if(!skip)out.append(decoded);}catch(Exception ignored){}i+=2;}continue;}
   if(!Character.isLetter(next))continue;int begin=i-1;while(i<value.length()&&Character.isLetter(value.charAt(i)))i++;String control=value.substring(begin,i);int number=0;boolean hasNumber=false,negative=false;
   if(i<value.length()&&value.charAt(i)=='-'){negative=true;i++;}while(i<value.length()&&Character.isDigit(value.charAt(i))){hasNumber=true;number=number*10+value.charAt(i++)-'0';}if(negative)number=-number;if(i<value.length()&&value.charAt(i)==' ')i++;
   if(Arrays.asList("fonttbl","colortbl","stylesheet","info","pict","object").contains(control)){skip=true;continue;}
   if(control.equals("uc")&&hasNumber){uc=Math.max(0,Math.min(10,number));continue;}
   if(!skip){if(control.equals("u")&&hasNumber){out.append((char)number);fallback=uc;}else if(control.equals("par")||control.equals("line"))out.append('\n');else if(control.equals("tab"))out.append('\t');else if(control.equals("emdash"))out.append('—');else if(control.equals("endash"))out.append('–');}
  }return out.toString().trim();
 }
 static List<String> epubOrder(ZipFile zip,List<String> fallback)throws Exception {
  ZipEntry container=zip.getEntry("META-INF/container.xml");if(container==null)return fallback;
  InputStream in=zip.getInputStream(container);String containerXml;try{containerXml=text(in);}finally{in.close();}
  XmlPullParserFactory factory=XmlPullParserFactory.newInstance();factory.setNamespaceAware(true);XmlPullParser p=factory.newPullParser();p.setInput(new StringReader(containerXml));String opf=null;int event;
  while((event=p.next())!=XmlPullParser.END_DOCUMENT)if(event==XmlPullParser.START_TAG&&p.getName().equals("rootfile")){opf=p.getAttributeValue(null,"full-path");break;}
  if(opf==null||zip.getEntry(opf)==null)return fallback;in=zip.getInputStream(zip.getEntry(opf));String opfXml;try{opfXml=text(in);}finally{in.close();}
  p=factory.newPullParser();p.setInput(new StringReader(opfXml));Map<String,String> items=new HashMap<String,String>();List<String> refs=new ArrayList<String>();
  while((event=p.next())!=XmlPullParser.END_DOCUMENT)if(event==XmlPullParser.START_TAG){if(p.getName().equals("item")){String id=p.getAttributeValue(null,"id"),href=p.getAttributeValue(null,"href");if(id!=null&&href!=null){java.net.URI uri=new java.net.URI(opf).resolve(href);items.put(id,uri.getPath());}}else if(p.getName().equals("itemref")&&!"no".equals(p.getAttributeValue(null,"linear")))refs.add(p.getAttributeValue(null,"idref"));}
  List<String> ordered=new ArrayList<String>();for(String ref:refs){String name=items.get(ref);if(name!=null&&zip.getEntry(name)!=null)ordered.add(name);}return ordered.isEmpty()?fallback:ordered;
 }
 private static String utc(){java.text.SimpleDateFormat f=new java.text.SimpleDateFormat("yyyy-MM-dd\'T\'HH:mm:ss\'Z\'",Locale.ROOT);f.setTimeZone(TimeZone.getTimeZone("UTC"));return f.format(new Date());}
 private static String esc(String s){return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;");}
 private static void entry(ZipOutputStream zip,String name,String text)throws Exception {zip.putNextEntry(new ZipEntry(name));zip.write(text.getBytes("UTF-8"));zip.closeEntry();}
 public static File write(String text,String fmt,File folder)throws Exception {
  File output=new File(folder,"document."+fmt);
  if(fmt.equals("pdf")){pdf(text,output);return output;}
  if(Arrays.asList("txt","md","html","rtf").contains(fmt)){
   Writer w=new OutputStreamWriter(new FileOutputStream(output),"UTF-8");
   if(fmt.equals("html"))w.write("<!doctype html><html><meta charset='utf-8'><body><pre dir='auto' style='white-space:pre-wrap'>"+esc(text)+"</pre></body></html>");
   else if(fmt.equals("rtf")){w.write("{\\rtf1\\ansi\\uc1 ");for(char c:text.toCharArray())if(c=='\n')w.write("\\par\n");else if(c=='\\'||c=='{'||c=='}')w.write("\\"+c);else if(c>127)w.write("\\u"+(short)c+"?");else w.write(c);w.write("}");}
   else w.write(text);w.close();return output;
  }
  ZipOutputStream zip=new ZipOutputStream(new FileOutputStream(output));try{
   if(fmt.equals("docx")){
    entry(zip,"[Content_Types].xml","<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/><Default Extension='xml' ContentType='application/xml'/><Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/></Types>");
    entry(zip,"_rels/.rels","<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/></Relationships>");
    StringBuilder xml=new StringBuilder("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>");for(String line:text.split("\n",-1)){boolean rtl=!new java.text.Bidi(line,java.text.Bidi.DIRECTION_DEFAULT_LEFT_TO_RIGHT).baseIsLeftToRight();xml.append("<w:p><w:pPr>").append(rtl?"<w:bidi/>":"").append("</w:pPr><w:r><w:t xml:space='preserve'>").append(esc(line)).append("</w:t></w:r></w:p>");}xml.append("</w:body></w:document>");entry(zip,"word/document.xml",xml.toString());
   }else if(fmt.equals("odt")){
    stored(zip,"mimetype","application/vnd.oasis.opendocument.text");entry(zip,"META-INF/manifest.xml","<manifest:manifest xmlns:manifest='urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'><manifest:file-entry manifest:full-path='/' manifest:media-type='application/vnd.oasis.opendocument.text'/><manifest:file-entry manifest:full-path='content.xml' manifest:media-type='text/xml'/></manifest:manifest>");
    StringBuilder xml=new StringBuilder("<office:document-content xmlns:office='urn:oasis:names:tc:opendocument:xmlns:office:1.0' xmlns:text='urn:oasis:names:tc:opendocument:xmlns:text:1.0' office:version='1.2'><office:body><office:text>");for(String line:text.split("\n",-1))xml.append("<text:p>").append(esc(line)).append("</text:p>");xml.append("</office:text></office:body></office:document-content>");entry(zip,"content.xml",xml.toString());
   }else if(fmt.equals("epub")){
    stored(zip,"mimetype","application/epub+zip");entry(zip,"META-INF/container.xml","<container version='1.0' xmlns='urn:oasis:names:tc:opendocument:xmlns:container'><rootfiles><rootfile full-path='book.opf' media-type='application/oebps-package+xml'/></rootfiles></container>");
    entry(zip,"book.opf","<package xmlns='http://www.idpf.org/2007/opf' version='3.0' unique-identifier='id'><metadata xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:identifier id='id'>urn:uuid:"+UUID.randomUUID()+"</dc:identifier><dc:title>Belge</dc:title><dc:language>und</dc:language><meta property='dcterms:modified'>"+utc()+"</meta></metadata><manifest><item id='nav' href='nav.xhtml' media-type='application/xhtml+xml' properties='nav'/><item id='text' href='text.xhtml' media-type='application/xhtml+xml'/></manifest><spine><itemref idref='text'/></spine></package>");
    entry(zip,"nav.xhtml","<html xmlns='http://www.w3.org/1999/xhtml' xmlns:epub='http://www.idpf.org/2007/ops'><head><title>İçindekiler</title></head><body><nav epub:type='toc'><ol><li><a href='text.xhtml'>Belge</a></li></ol></nav></body></html>");
    entry(zip,"text.xhtml","<html xmlns='http://www.w3.org/1999/xhtml'><head><meta charset='UTF-8'/><title>Belge</title></head><body><pre dir='auto'>"+esc(text)+"</pre></body></html>");
   }else throw new IOException("Unsupported output format");
  }finally{zip.close();}return output;
 }
 private static void stored(ZipOutputStream zip,String name,String value)throws Exception {byte[]b=value.getBytes("UTF-8");CRC32 crc=new CRC32();crc.update(b);ZipEntry e=new ZipEntry(name);e.setMethod(ZipEntry.STORED);e.setSize(b.length);e.setCompressedSize(b.length);e.setCrc(crc.getValue());zip.putNextEntry(e);zip.write(b);zip.closeEntry();}
 private static void pdf(String text,File output)throws Exception {
  PdfDocument document=new PdfDocument();TextPaint paint=new TextPaint(Paint.ANTI_ALIAS_FLAG);paint.setColor(Color.BLACK);paint.setTextSize(12);int width=515;StaticLayout layout=new StaticLayout(text,paint,width,Layout.Alignment.ALIGN_NORMAL,1.2f,0,false);int first=0,page=1;
  try{while(first<layout.getLineCount()){
   int top=layout.getLineTop(first),last=first;while(last<layout.getLineCount()&&layout.getLineBottom(last)-top<750)last++;if(last==first)last++;
   PdfDocument.Page p=document.startPage(new PdfDocument.PageInfo.Builder(595,842,page++).create());Canvas c=p.getCanvas();c.save();c.translate(40,40-top);c.clipRect(0,top,width,layout.getLineBottom(last-1));layout.draw(c);c.restore();document.finishPage(p);first=last;
  }FileOutputStream stream=new FileOutputStream(output);try{document.writeTo(stream);}finally{stream.close();}}finally{document.close();}
  preserveLogicalText(output,text);
 }
 private static final String TEXT_NS="urn:donusturucu:logical-text:1.0";
 private static String contentHash(PDDocument doc)throws Exception {
  java.security.MessageDigest hash=java.security.MessageDigest.getInstance("SHA-256");byte[]buffer=new byte[8192];
  for(PDPage page:doc.getPages()){hash.update((page.getCropBox().toString()+":"+page.getRotation()+"\n").getBytes("UTF-8"));InputStream stream=page.getContents();if(stream!=null)try{int n;while((n=stream.read(buffer))!=-1)hash.update(buffer,0,n);}finally{stream.close();}}
  StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format(Locale.ROOT,"%02x",b&255));return hex.toString();
 }
 static void preserveLogicalText(File output,String text)throws Exception {
  PDDocument doc=PDDocument.load(output);File temp=new File(output.getParentFile(),"logical-"+output.getName());
  try{String hash=contentHash(doc);String xml="<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'><rdf:Description xmlns:d='"+TEXT_NS+"'><d:hash>"+hash+"</d:hash><d:text>"+android.util.Base64.encodeToString(text.getBytes("UTF-8"),android.util.Base64.NO_WRAP)+"</d:text></rdf:Description></rdf:RDF></x:xmpmeta>";
   com.tom_roush.pdfbox.pdmodel.common.PDMetadata metadata=new com.tom_roush.pdfbox.pdmodel.common.PDMetadata(doc);metadata.importXMPMetadata(xml.getBytes("UTF-8"));doc.getDocumentCatalog().setMetadata(metadata);doc.save(temp);
  }finally{doc.close();}
  InputStream in=new FileInputStream(temp);OutputStream out=new FileOutputStream(output);try{byte[]b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}finally{in.close();out.close();temp.delete();}
 }
 private static String logicalText(PDDocument doc)throws Exception {
  com.tom_roush.pdfbox.pdmodel.common.PDMetadata metadata=doc.getDocumentCatalog().getMetadata();if(metadata==null)return null;
  try{InputStream input=metadata.exportXMPMetadata();String xml;try{xml=text(input);}finally{input.close();}XmlPullParserFactory factory=XmlPullParserFactory.newInstance();factory.setNamespaceAware(true);XmlPullParser parser=factory.newPullParser();parser.setInput(new StringReader(xml));String hash=null,logical=null;int event;
   while((event=parser.next())!=XmlPullParser.END_DOCUMENT)if(event==XmlPullParser.START_TAG&&TEXT_NS.equals(parser.getNamespace())){if(parser.getName().equals("hash"))hash=parser.nextText();else if(parser.getName().equals("text"))logical=parser.nextText();}
   if(hash!=null&&logical!=null&&hash.equals(contentHash(doc)))return new String(android.util.Base64.decode(logical,android.util.Base64.DEFAULT),"UTF-8");
  }catch(Exception ignored){}return null;
 }
 public static List<File> pages(File source,File other,String action,int count,File folder)throws Exception {
  PDDocument doc=PDDocument.load(source);List<File> out=new ArrayList<File>();try{
   if(action.equals("merge")){PDDocument second=PDDocument.load(other);try{PDDocument merged=new PDDocument();try{for(PDPage p:doc.getPages())merged.importPage(p);for(PDPage p:second.getPages())merged.importPage(p);File f=new File(folder,"merged.pdf");merged.save(f);out.add(f);}finally{merged.close();}}finally{second.close();}}
   else{if(count<1)throw new IllegalArgumentException("Invalid page count");for(int i=0;i<doc.getNumberOfPages();i+=count){PDDocument part=new PDDocument();try{for(int j=i;j<Math.min(i+count,doc.getNumberOfPages());j++)part.importPage(doc.getPage(j));File f=new File(folder,"part-"+(out.size()+1)+".pdf");part.save(f);out.add(f);}finally{part.close();}}}
  }finally{doc.close();}return out;
 }
}
