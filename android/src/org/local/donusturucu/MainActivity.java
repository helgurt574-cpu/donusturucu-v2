package org.local.donusturucu;
import android.app.*;import android.os.*;import android.content.*;import android.database.Cursor;import android.net.Uri;import android.provider.*;import android.view.*;import android.widget.*;import android.graphics.*;import android.graphics.drawable.*;import android.system.Os;import android.media.MediaPlayer;import android.text.*;
import java.io.*;import java.util.*;import java.util.zip.*;import org.json.*;
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader;

public class MainActivity extends Activity {
 static final String VERSION="1.4.4";
 static class ListedFile {File file;String name,ext;MediaEngine.Info info;File thumb;ListedFile(File f,String n,String e,MediaEngine.Info i){file=f;name=n;ext=e;info=i;}}
 /** Result of the preview button: a comparison, a short clip or sound, thumbnails or text. */
 static final class Preview {String action,kind,note,text;Bitmap before,after;File original,result;float[] peaksA,peaksB;List<Bitmap> thumbs=new ArrayList<Bitmap>();List<String> captions=new ArrayList<String>();boolean showResult=true;}

 // ---- engine state (the self tests use these too)
 private final List<ListedFile> files=new ArrayList<ListedFile>();private int selectedIndex=-1;
 private File source,other;private MediaEngine.Info info,otherInfo;private String display="",otherDisplay="",ext="",otherExt="",action="convert",targetFormat="";
 private OcrEngine ocr;private volatile boolean busy=false,cancelled=false,ready=false;private volatile java.lang.Process process;private File libraries;private final StringBuilder log=new StringBuilder();
 private Uri outputTree;private boolean ku=false,batchEnabled=false,pendingStart=false;
 // ---- look and screen state
 private String themeMode="system",screen="home",builtScreen="";private int accentIndex=0,qualityChoice=0;private boolean flipAnim=false,dark,toolsTab=false,donutBack=false,showLog=false;private Ui ui;
 private final Map<String,String> vals=new HashMap<String,String>();private final List<double[]> regions=new ArrayList<double[]>();
 private Bitmap base;private int pdfPage=0,pdfCount=0;private double frameAt=-1;private String excerpt;private float[] peaks;private int loadToken=0;private boolean playSource=false;
 private Preview preview;private String homeNotice;private boolean openImported=false;private final List<Uri> lastOutputs=new ArrayList<Uri>();private final List<String> lastMimes=new ArrayList<String>();private String lastSummary,lastStatus="";private File publishingThumb;
 private volatile double progressTotal=0;private volatile int batchIndex=0,batchCount=1;
 // ---- views
 private ScrollView scroller;private LinearLayout page;private TextView status,percent;private ProgressBar progress;private VideoView video;private MediaPlayer player;private final Handler handler=new Handler(Looper.getMainLooper());
 private final java.util.concurrent.ExecutorService light=java.util.concurrent.Executors.newSingleThreadExecutor();

 private String t(String tr,String kr){return ku?kr:tr;}
 private int dp(float x){return ui.dp(x);}
 private void palette(){int night=getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK;dark=themeMode.equals("dark")||(themeMode.equals("system")&&night==android.content.res.Configuration.UI_MODE_NIGHT_YES);ui=new Ui(this,dark,accentIndex);}
 @Override public void onConfigurationChanged(android.content.res.Configuration c){super.onConfigurationChanged(c);boolean was=dark;palette();if(was!=dark&&!busy)build();}

 public void onCreate(Bundle state){SharedPreferences p=getPreferences(0);themeMode=p.getString("theme","system");accentIndex=p.getInt("accent",0);ku=p.getBoolean("ku",false);palette();
  setTheme(dark?android.R.style.Theme_Material_NoActionBar:android.R.style.Theme_Material_Light_NoActionBar);super.onCreate(state);
  registerBack();String saved=p.getString("tree",null);if(saved!=null)outputTree=Uri.parse(saved);PDFBoxResourceLoader.init(this);build();
  new Thread(new Runnable(){public void run(){try{prepareNative();ready=true;message(t("Hazır. Dosyanı seçebilirsin.","Amade ye. Dosyeya xwe hilbijêre."));runOnUiThread(new Runnable(){public void run(){if(!busy&&!screen.equals("work"))build();}});
   Intent in=getIntent();
   if(in.getBooleanExtra("orientation_test",false))OrientationSelfTest.run(MainActivity.this);if(in.getBooleanExtra("detection_test",false))DetectionSelfTest.run(MainActivity.this);if(in.getBooleanExtra("rich_test",false))FeatureSelfTest.rich(MainActivity.this);
   if(in.getBooleanExtra("full_test",false))FullSelfTest.run(MainActivity.this);if(in.getBooleanExtra("release_test",false))ReleaseSelfTest.run(MainActivity.this);if(in.getBooleanExtra("feature_test",false))FeatureSelfTest.run(MainActivity.this,in.getBooleanExtra("speech_test",false));
   if(in.getBooleanExtra("self_test",false))AndroidSelfTest.run(MainActivity.this);if(in.getBooleanExtra("document_matrix",false))AndroidSelfTest.documents(MainActivity.this);if(in.getBooleanExtra("tools_test",false))ToolsSelfTest.run(MainActivity.this);
  }catch(Exception e){failure(e);}}}).start();
  receive(getIntent());}
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);receive(i);}
 /** Files sent with "Share → Dönüştürücü" or "Open with". */
 private void receive(Intent in){if(in==null)return;List<Uri> uris=new ArrayList<Uri>();String a=in.getAction();
  try{if(Intent.ACTION_SEND.equals(a)){Uri u=in.getParcelableExtra(Intent.EXTRA_STREAM);if(u!=null)uris.add(u);}
   else if(Intent.ACTION_SEND_MULTIPLE.equals(a)){ArrayList<Uri> list=in.getParcelableArrayListExtra(Intent.EXTRA_STREAM);if(list!=null)uris.addAll(list);}
   else if(Intent.ACTION_VIEW.equals(a)&&in.getData()!=null)uris.add(in.getData());}catch(Exception ignored){}
  if(!uris.isEmpty()){quickAction=in.getStringExtra("quick_action");quickFormat=in.getStringExtra("quick_format");in.removeExtra("quick_action");in.removeExtra("quick_format");
   in.setAction(Intent.ACTION_MAIN);openImported=true;importMany(uris,null);}}
 /** A format or tool picked in the quick viewer: a format starts at once, a tool opens with its settings. */
 private String quickAction,quickFormat;
 private void applyQuick(){String a=quickAction,f=quickFormat;quickAction=null;quickFormat=null;if(a==null||source==null||busy)return;
  if(a.equals("convert")){toolsTab=false;action="convert";if(f!=null&&Arrays.asList(formatValues(info,ext)).contains(f)){targetFormat=f;donutBack=!Arrays.asList(frontFormats(info,ext)).contains(f);build();startJob();}else build();return;}
  for(String[] x:offeredActions(info,ext))if(x[0].equals(a)){toolsTab=true;chooseTool(a);return;}
  build();}
 private void chooseTool(String id){if(busy)return;action=id;preview=null;lastSummary=null;build();scroller.post(new Runnable(){public void run(){if(action.equals("watermark")&&(ext.equals("image")||(info!=null&&info.video))){scroller.smoothScrollTo(0,0);toast(t("Görüntüde filigranın üstünü çerçevele.","Li ser wêneyê nîşana avê çarçove bike."));return;}
   if(info!=null&&TIMED.contains(action)){scroller.smoothScrollTo(0,0);toast(t("Oynatıcıyı istediğin yerde durdur, sonra “Başlangıç / Bitiş = bu an”a dokun.","Lîstikvanê li cihê xwestî rawestîne, paşê “Destpêk / Dawî = niha” bitikîne."));return;}View o=page.findViewWithTag("options");if(o!=null)scroller.smoothScrollTo(0,Math.max(0,o.getTop()-dp(12)));}});}

 // =====================================================================================
 // Screen
 // =====================================================================================
 private LinearLayout root;private FrameLayout headerBox,navBox;private String lookKey="";
 private View sourceView,previewView;private String sourceKey="",previewKey="";private int sourceVersion=0;
 /** The window is made once per look (theme, colour, language); later calls only refill the page
  *  in place, so the scroll position stays put and nothing flashes. */
 private void build(){
  String look=dark+"/"+accentIndex+"/"+ku;boolean same=screen.equals(builtScreen);
  if(root==null||!look.equals(lookKey)){stopMedia();lookKey=look;same=false;
   root=ui.column();root.setBackgroundColor(ui.bg);headerBox=new FrameLayout(this);root.addView(headerBox);
   scroller=new ScrollView(this);scroller.setFillViewport(true);scroller.setVerticalScrollBarEnabled(false);page=ui.column();page.setPadding(dp(18),dp(4),dp(18),dp(32));scroller.addView(page);root.addView(scroller,new LinearLayout.LayoutParams(-1,0,1));
   navBox=new FrameLayout(this);root.addView(navBox);setContentView(root);final LinearLayout r=root;
   getWindow().setStatusBarColor(ui.bg);getWindow().setNavigationBarColor(ui.surface);getWindow().getDecorView().setSystemUiVisibility(dark?0:(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR));
  getWindow().getDecorView().setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener(){public WindowInsets onApplyWindowInsets(View v,WindowInsets i){r.setPadding(i.getSystemWindowInsetLeft(),i.getSystemWindowInsetTop(),i.getSystemWindowInsetRight(),i.getSystemWindowInsetBottom());return i;}});
  getWindow().getDecorView().requestApplyInsets();
  }
  if(!screen.equals("work")&&sourceView!=null)stopMedia();
  builtScreen=screen;headerBox.removeAllViews();headerBox.addView(header());navBox.removeAllViews();navBox.addView(nav());
  scroller.setDescendantFocusability(ViewGroup.FOCUS_BLOCK_DESCENDANTS);page.setMinimumHeight(same?page.getHeight():0);page.removeAllViews();
  status=null;percent=null;progress=null;regionNote=null;
  if(screen.equals("work")&&source!=null)buildWork();else if(screen.equals("history"))buildHistory();else if(screen.equals("settings"))buildSettings();else{screen="home";buildHome();}
  scroller.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);if(!same)scroller.scrollTo(0,0);
 }
 private void go(String where){if(!where.equals("home"))homeNotice=null;if(!where.equals(screen))builtScreen="";screen=where;build();}
 private View header(){
  LinearLayout h=ui.row();h.setPadding(dp(14),dp(10),dp(14),dp(8));
  if(screen.equals("work")&&source!=null){
   TextView back=iconButton("back",new View.OnClickListener(){public void onClick(View v){go("home");}});h.addView(back);
   LinearLayout col=ui.column();TextView name=ui.label(display,17,ui.text,true);name.setSingleLine(true);name.setEllipsize(TextUtils.TruncateAt.MIDDLE);col.addView(name);col.addView(ui.small(meta(new ListedFile(source,display,ext,info))));
   h.addView(col,new LinearLayout.LayoutParams(0,-2,1));
  }else{
   ImageView logo=new ImageView(this);try{logo.setImageDrawable(getPackageManager().getApplicationIcon(getPackageName()));}catch(Exception ignored){}h.addView(logo,new LinearLayout.LayoutParams(dp(40),dp(40)));
   LinearLayout col=ui.column();col.setPadding(dp(12),0,0,0);col.addView(ui.label(t("Dönüştürücü","Veguherîner"),19,ui.text,true));col.addView(ui.small(t("Seç · önizle · dönüştür","Hilbijêre · pêşdîtin · veguherîne")));h.addView(col,new LinearLayout.LayoutParams(0,-2,1));
   if(!ready){ProgressBar spin=new ProgressBar(this);spin.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(ui.accent));h.addView(spin,new LinearLayout.LayoutParams(dp(22),dp(22)));}
  }
  return h;}
 private TextView iconButton(String icon,View.OnClickListener l){TextView b=new TextView(this);Drawable d=ui.icon(icon,ui.text,22);b.setCompoundDrawablesRelative(d,null,null,null);b.setPadding(dp(10),dp(10),dp(10),dp(10));b.setBackground(ui.ripple(ui.round(0,22,0),22));b.setOnClickListener(l);b.setClickable(true);return b;}
 private View nav(){
  LinearLayout bar=ui.row();bar.setBackgroundColor(ui.surface);bar.setPadding(dp(8),dp(6),dp(8),dp(8));
  String[][] items={{"home","home",t("Ana sayfa","Destpêk")},{"history","history",t("Geçmiş","Dîrok")},{"settings","tune",t("Ayarlar","Mîheng")}};
  for(final String[] it:items){boolean on=screen.equals(it[0])||(it[0].equals("home")&&screen.equals("work"));
   LinearLayout cell=ui.column();cell.setGravity(Gravity.CENTER_HORIZONTAL);cell.setPadding(0,dp(4),0,dp(2));
   FrameLayout pill=new FrameLayout(this);pill.setBackground(ui.round(on?ui.accentSoft:0,16,0));ImageView i=new ImageView(this);i.setImageDrawable(ui.icon(it[1],on?ui.accentText:ui.muted,22));pill.addView(i,new FrameLayout.LayoutParams(dp(22),dp(22),Gravity.CENTER));
   cell.addView(pill,new LinearLayout.LayoutParams(dp(60),dp(32)));TextView l=ui.label(it[2],12,on?ui.accentText:ui.muted,on);l.setPadding(0,dp(3),0,0);l.setGravity(Gravity.CENTER);cell.addView(l);
   cell.setBackground(ui.ripple(ui.round(0,16,0),16));cell.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(it[0].equals("home")&&screen.equals("work")){go("home");return;}if(!screen.equals(it[0]))go(it[0]);}});
   bar.addView(cell,new LinearLayout.LayoutParams(0,-2,1));}
  LinearLayout wrap=ui.column();View line=new View(this);line.setBackgroundColor(ui.border);wrap.addView(line,new LinearLayout.LayoutParams(-1,dp(1)));wrap.addView(bar);return wrap;}

 // ---- home
 private void buildHome(){
  page.addView(ui.title(t("Ana sayfa","Destpêk")));page.addView(ui.space(12));
  LinearLayout drop=ui.column();drop.setGravity(Gravity.CENTER_HORIZONTAL);drop.setPadding(dp(18),dp(22),dp(18),dp(20));
  GradientDrawable g=ui.round(ui.surface2,22,0);g.setStroke(dp(1.5f),ui.blend(ui.accent,ui.surface2,0.55f),dp(7),dp(5));drop.setBackground(ui.ripple(g,22));drop.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(!busy)choose(1);}});
  FrameLayout circle=ui.badge("upload",64,ui.accentSoft,ui.accentText);circle.setBackground(ui.round(ui.accentSoft,32,0));drop.addView(circle);
  TextView head=ui.label(t("Dosyalarını buraya getir","Dosyeyên xwe li vir bîne"),18,ui.text,true);head.setGravity(Gravity.CENTER);head.setPadding(0,dp(12),0,dp(4));drop.addView(head);
  TextView hint=ui.body(t("Video, ses, PDF, belge veya fotoğraf seç. Galeri ya da Dosyalar'da “Paylaş → Dönüştürücü” ile de gönderebilirsin.","Vîdyo, deng, PDF, belge an wêne hilbijêre. Ji Galeriyê an Dosyeyan bi “Parve bike → Veguherîner” jî dikarî bişînî."));hint.setGravity(Gravity.CENTER);drop.addView(hint);
  LinearLayout buttons=ui.row();buttons.setPadding(0,dp(14),0,0);
  TextView pick=ui.button(t("Dosya seç","Dosye hilbijêre"),"add",0,new View.OnClickListener(){public void onClick(View v){choose(1);}});TextView fold=ui.button(t("Klasör ekle","Peldank"),"folder",1,new View.OnClickListener(){public void onClick(View v){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(i,4);}});
  buttons.addView(pick,ui.weight(1));buttons.addView(new View(this),new LinearLayout.LayoutParams(dp(10),1));buttons.addView(fold,ui.weight(1));drop.addView(buttons,new LinearLayout.LayoutParams(-1,-2));
  ui.enable(pick,!busy);ui.enable(fold,!busy);page.addView(drop);
  statusCard(page,false);
  if(!files.isEmpty()){
   LinearLayout head2=ui.row();head2.setPadding(0,dp(14),0,dp(6));TextView sec=ui.section(t("Dosyalar","Dosye")+" · "+files.size());sec.setPadding(0,0,0,0);head2.addView(sec,new LinearLayout.LayoutParams(0,-2,1));
   TextView clear=ui.button(t("Temizle","Paqij bike"),null,2,new View.OnClickListener(){public void onClick(View v){clearFiles();}});clear.setMinHeight(0);clear.setPadding(dp(14),dp(6),dp(14),dp(6));clear.setTextSize(13);ui.enable(clear,!busy);head2.addView(clear);page.addView(head2);
   for(int n=0;n<files.size();n++)page.addView(fileRow(n));
   page.addView(ui.small(t("Listeden kaldırmak orijinal dosyayı silmez.","Rakirin ji lîsteyê dosyeya resen jê nabe.")));
  }
  JSONArray h=history();if(h.length()>0){LinearLayout head3=ui.row();head3.setPadding(0,dp(14),0,dp(6));TextView sec3=ui.section(t("Son dönüştürmeler","Veguherînên dawî"));sec3.setPadding(0,0,0,0);head3.addView(sec3,new LinearLayout.LayoutParams(0,-2,1));
   TextView all=ui.button(t("Tümü","Hemû"),null,2,new View.OnClickListener(){public void onClick(View v){go("history");}});all.setMinHeight(0);all.setPadding(dp(14),dp(6),dp(14),dp(6));all.setTextSize(13);head3.addView(all);page.addView(head3);
   for(int i=0;i<Math.min(3,h.length());i++)page.addView(historyRow(h.optJSONObject(i)));}
  else if(files.isEmpty()){page.addView(ui.section(t("Son dönüştürmeler","Veguherînên dawî")));page.addView(ui.body(t("Dönüştürdüğün dosyalar burada görünür.","Dosyeyên ku tu diguherînî li vir xuya dibin.")));}
 }
 private View fileRow(final int n){final ListedFile f=files.get(n);LinearLayout row=ui.row();row.setPadding(dp(10),dp(10),dp(6),dp(10));row.setBackground(ui.ripple(ui.round(ui.surface,16,ui.border),16));
  LinearLayout.LayoutParams lp=ui.margins(-1,-2,0,0,0,8);row.setLayoutParams(lp);row.addView(thumb(f.thumb,iconFor(f),52));
  LinearLayout col=ui.column();col.setPadding(dp(12),0,dp(4),0);TextView name=ui.label(f.name,15,ui.text,true);name.setSingleLine(true);name.setEllipsize(TextUtils.TruncateAt.MIDDLE);col.addView(name);col.addView(ui.small(meta(f)));row.addView(col,new LinearLayout.LayoutParams(0,-2,1));
  TextView remove=iconButton("close",new View.OnClickListener(){public void onClick(View v){if(busy)return;files.remove(n).file.delete();if(selectedIndex==n){selectedIndex=-1;resetFile();}else if(selectedIndex>n)selectedIndex--;build();}});row.addView(remove);
  row.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(!busy)selectFile(n);}});return row;}
 private View thumb(File file,String icon,int size){
  if(file!=null&&file.isFile()){Bitmap b=BitmapFactory.decodeFile(file.getAbsolutePath());if(b!=null){ImageView i=new ImageView(this);i.setImageBitmap(b);i.setScaleType(ImageView.ScaleType.CENTER_CROP);i.setBackground(ui.round(ui.surface2,12,0));i.setClipToOutline(true);i.setLayoutParams(new LinearLayout.LayoutParams(dp(size),dp(size)));return i;}}
  return ui.badge(icon,size,ui.accentSoft,ui.accentText);}
 static String iconFor(ListedFile f){if(f.info!=null)return f.info.video?"video":"audio";if(f.ext.equals("image"))return "image";if(f.ext.equals("srt"))return "subtitles";return "doc";}
 private String kind(ListedFile f){if(f.info!=null)return f.info.video?t("Video","Vîdyo"):t("Ses","Deng");if(f.ext.equals("image"))return t("Fotoğraf","Wêne");if(f.ext.equals("srt"))return t("Altyazı","Binnivîs");return f.ext.toUpperCase(Locale.ROOT);}
 private String meta(ListedFile f){StringBuilder b=new StringBuilder(kind(f));if(f.info!=null){b.append(" · ").append(clock(f.info.duration));if(f.info.video&&f.info.width>0)b.append(" · ").append(f.info.shownWidth()).append('×').append(f.info.shownHeight());}b.append(" · ").append(size(f.file.length()));return b.toString();}
 static String clock(double s){int x=(int)Math.round(s);return x>=3600?String.format(Locale.ROOT,"%d:%02d:%02d",x/3600,(x/60)%60,x%60):String.format(Locale.ROOT,"%d:%02d",x/60,x%60);}
 static String size(long b){if(b<1024)return b+" B";if(b<1024*1024)return String.format(Locale.ROOT,"%.0f KB",b/1024.0);if(b<1024L*1024*1024)return String.format(Locale.ROOT,"%.1f MB",b/1048576.0);return String.format(Locale.ROOT,"%.2f GB",b/1073741824.0);}

 // ---- file workspace
 private void resetFile(){sourceVideoAt=new int[1];source=null;info=null;display="";ext="";other=null;otherInfo=null;otherDisplay="";otherExt="";action="convert";targetFormat="";vals.clear();regions.clear();base=null;pdfPage=0;pdfCount=0;frameAt=-1;excerpt=null;peaks=null;preview=null;lastSummary=null;toolsTab=false;donutBack=false;playSource=false;}
 private void selectFile(int index){if(busy)return;resetFile();selectedIndex=index;if(index<0||index>=files.size()){go("home");return;}ListedFile f=files.get(index);source=f.file;display=f.name;ext=f.ext;info=f.info;screen="work";go("work");loadBase();}
 private void clearFiles(){if(busy)return;for(ListedFile f:files){f.file.delete();if(f.thumb!=null)f.thumb.delete();}files.clear();selectedIndex=-1;batchEnabled=false;resetFile();build();}
 /** Picture, page, waveform or text of the selected file, made in the background. */
 private void loadBase(){final int token=++loadToken;final File src=source;final String e=ext;final MediaEngine.Info in=info;final int pageNo=pdfPage;final double at=frameAt;
  light.execute(new Runnable(){public void run(){try{
   Bitmap b=null;float[] w=null;String text=null;int count=pdfCount;
   if(in!=null&&in.video){File dir=new File(getCacheDir(),"base");dir.mkdirs();File still=lightEngine(dir).still(src,at>=0?at:Math.min(1,in.duration*0.1),1280,"frame-"+token);b=BitmapFactory.decodeFile(still.getAbsolutePath());still.delete();}
   else if(in!=null){w=wavePeaks(src,90);}
   else if(e.equals("pdf")||pagedExt(e)){File pdf=viewPdf(src,e,token);count=Tools.pageCount(pdf);b=Tools.renderPage(pdf,Math.min(pageNo,Math.max(0,count-1)),1100);}
   else if(e.equals("image")){b=Tools.load(src,1600);}
   else{String s=e.equals("srt")||e.equals("txt")?readFile(src):DocumentEngine.read(src,e);text=s.length()>1800?s.substring(0,1800)+"…":s;}
   final Bitmap fb=b;final float[] fw=w;final String ft=text;final int fc=count;
   runOnUiThread(new Runnable(){public void run(){if(token!=loadToken||source!=src)return;boolean had=base!=null;pdfCount=fc;if(fw!=null)peaks=fw;
    // Next page or another frame: fade the new picture in, nothing else is rebuilt.
    if(had&&fb!=null&&ft==null&&sourcePicture!=null&&screen.equals("work")){base=fb;sourcePicture.crossfade(fb);if(pageLabel!=null)pageLabel.setText(pageText());return;}
    base=fb;excerpt=ft;if(screen.equals("work"))build();}});
  }catch(Exception ex){runOnUiThread(new Runnable(){public void run(){if(token==loadToken&&source==src){excerpt=t("Önizleme hazırlanamadı.","Pêşdîtin nehat amadekirin.");if(screen.equals("work"))build();}}});}}});}

 /** Documents shown page by page (as PDF), like the PDF files themselves. */
 static boolean pagedExt(String e){return Arrays.asList("docx","odt","epub","html","htm","txt","md","rtf","pptx","odp","xlsx","csv","tsv","rst").contains(e);}
 private final Map<File,File> viewPdfs=new HashMap<File,File>();
 private File viewPdf(File src,String e,int token)throws Exception{if(e.equals("pdf"))return src;File done=viewPdfs.get(src);if(done!=null&&done.isFile())return done;
  File dir=new File(getCacheDir(),"view-"+token);dir.mkdirs();File out;RichDocument.Host host=new RichDocument.Host(){public void check(){}};
  try{out=Arrays.asList("docx","odt","epub","html","htm").contains(e)?RichDocument.read(src,e,host).write("pdf",dir,host):DocumentEngine.write(DocumentEngine.read(src,e),"pdf",dir);}
  catch(Exception rich){out=DocumentEngine.write(DocumentEngine.read(src,e),"pdf",dir);}
  viewPdfs.put(src,out);return out;}
 private boolean paged(){return info==null&&(ext.equals("pdf")||pagedExt(ext));}
 private String pageText(){return t("Sayfa ","Rûpel ")+(pdfPage+1)+" / "+pdfCount;}
 private java.util.concurrent.Callable<Double> sourcePos;private int[] sourceVideoAt=new int[1];private Widgets.Picture sourcePicture;private TextView pageLabel;private View sourceMarks;private final Map<String,EditText> fieldViews=new HashMap<String,EditText>();
 static final Set<String> TIMED=new HashSet<String>(Arrays.asList("trim","remove","split","mute_range","gif","frame","rotate","speed","volume","fade_in","fade_out","extract","transcribe","add","replace"));
 static String tclock(double s){s=Math.max(0,s);int h=(int)(s/3600),m=(int)(s%3600/60);String sec=String.format(Locale.ROOT,"%04.1f",s%60);return h>0?h+":"+String.format(Locale.ROOT,"%02d",m)+":"+sec:m+":"+sec;}
 /** Start/end of the tool from where the player stands; only the field changes, the video keeps its place. */
 private void markTime(String key,double at){if(!TIMED.contains(action))return;if(action.equals("frame"))key="start";String v=tclock(at);put(key,v);preview=null;EditText e=fieldViews.get(key);if(e!=null)e.setText(v);toast((key.equals("start")?t("Başlangıç: ","Destpêk: "):t("Bitiş: ","Dawî: "))+v);}
 private View marksRow(final java.util.concurrent.Callable<Double> where){LinearLayout r=ui.row();r.setPadding(0,dp(8),0,0);
  for(final String k:new String[]{"start","end"}){TextView b=ui.chip(k.equals("start")?t("Başlangıç = bu an","Destpêk = niha"):t("Bitiş = bu an","Dawî = niha"),false,new View.OnClickListener(){public void onClick(View v){try{markTime(k,where.call());}catch(Exception ignored){}}});
   LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);lp.setMargins(0,0,dp(k.equals("start")?8:0),0);r.addView(b,lp);}
  return r;}
 private void buildWork(){
  // The picture/player and the preview survive refreshes: a playing video keeps playing.
  fieldViews.clear();String sk=sourceKeyNow(),pk=preview!=null&&action.equals(preview.action)?System.identityHashCode(preview)+"|"+preview.kind+"|"+preview.showResult:"";
  if(sourceView==null||!sk.equals(sourceKey)||!pk.equals(previewKey)){stopMedia();sourceView=sourceCard();sourceKey=sk;previewView=pk.length()==0?null:previewCard();previewKey=pk;}
  page.addView(sourceView);if(sourceMarks!=null)sourceMarks.setVisibility(toolsTab&&TIMED.contains(action)?View.VISIBLE:View.GONE);
  List<String[]> acts=offeredActions(info,ext);boolean hasTools=acts.size()>1,hasConvert=!acts.isEmpty()&&acts.get(0)[0].equals("convert");
  if(!hasConvert)toolsTab=true;if(!hasTools)toolsTab=false;
  if(toolsTab&&action.equals("convert")&&hasConvert){}else if(!toolsTab)action=hasConvert?"convert":acts.get(0)[0];
  if(hasTools&&hasConvert){page.addView(ui.space(14));page.addView(segmented(new String[]{t("Dönüştür","Veguherîne"),t("Araçlar","Amûr")+" · "+(acts.size()-1)},toolsTab?1:0,new int[]{0,1},new Pick(){public void pick(int i){if(busy)return;toolsTab=i==1;if(!toolsTab)action="convert";else if(action.equals("convert"))action="";preview=null;build();}}));}
  if(!toolsTab)page.addView(convertCard());
  else{page.addView(toolGrid(acts));if(action.length()>0&&!action.equals("convert"))page.addView(optionsCard());}
  if(action.length()==0)return;
  if(files.size()>1){CheckBox all=new CheckBox(this);all.setText(t("Listedeki uygun bütün dosyalara uygula","Li hemû pelên guncav ên lîsteyê bi kar bîne")+" ("+files.size()+")");all.setTextColor(ui.text);all.setButtonTintList(android.content.res.ColorStateList.valueOf(ui.accent));all.setChecked(batchEnabled);all.setEnabled(!busy);all.setPadding(dp(4),dp(10),0,dp(10));
   all.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener(){public void onCheckedChanged(CompoundButton b,boolean c){batchEnabled=c;}});page.addView(all);}
  LinearLayout row=ui.row();row.setPadding(0,dp(14),0,0);
  TextView look=ui.button(t("Önizle","Pêşdîtin"),"eye",1,new View.OnClickListener(){public void onClick(View v){runPreview();}});
  TextView go=ui.button(t("Başlat","Dest pê bike"),"play",0,new View.OnClickListener(){public void onClick(View v){startJob();}});
  row.addView(look,ui.weight(1));row.addView(new View(this),new LinearLayout.LayoutParams(dp(10),1));row.addView(go,ui.weight(1.3f));page.addView(row);
  ui.enable(look,!busy&&previewable(action));ui.enable(go,!busy);
  if(outputTree==null)page.addView(note(t("Başlattığında kaydedilecek klasörü bir kez seçmen istenecek.","Dema tu dest pê dikî, carekê peldanka tomarkirinê tê xwestin.")));
  statusCard(page,true);
  if(previewView!=null)page.addView(previewView);
  if(lastSummary!=null)page.addView(resultCard());
  TextView logs=ui.button(showLog?t("İşlem ayrıntılarını gizle","Hûrgiliyan veşêre"):t("İşlem ayrıntılarını göster","Hûrgiliyan nîşan bide"),"info",2,new View.OnClickListener(){public void onClick(View v){showLog=!showLog;build();}});page.addView(ui.space(12));page.addView(logs);
  if(showLog){TextView d=ui.small(log.length()==0?"—":log.toString());d.setTextIsSelectable(true);d.setPadding(dp(4),dp(8),dp(4),0);page.addView(d);}
 }
 private TextView note(String s){TextView v=ui.small(s);v.setPadding(dp(4),dp(8),dp(4),0);return v;}
 interface Pick {void pick(int i);}
 /** Pill-shaped two- or three-way switch. */
 private View segmented(String[] labels,int selected,final int[] values,final Pick p){LinearLayout box=ui.row();box.setBackground(ui.round(ui.surface2,24,ui.border));box.setPadding(dp(4),dp(4),dp(4),dp(4));
  for(int i=0;i<labels.length;i++){final int v=values[i];boolean on=i==selected;TextView s=ui.label(labels[i],14,on?ui.onAccent:ui.text,true);s.setGravity(Gravity.CENTER);s.setPadding(dp(10),dp(9),dp(10),dp(9));s.setBackground(on?ui.round(ui.accent,20,0):ui.ripple(ui.round(0,20,0),20));
   s.setOnClickListener(new View.OnClickListener(){public void onClick(View x){p.pick(v);}});box.addView(s,ui.weight(1));}return box;}

 /** Preview of the file itself; for watermarks the user frames the mark here. */
 private View sourceCard(){
  LinearLayout card=ui.card();card.setPadding(dp(10),dp(10),dp(10),dp(12));sourcePicture=null;pageLabel=null;sourceMarks=null;sourcePos=null;boolean marking=action.equals("watermark")&&(ext.equals("pdf")||ext.equals("image")||(info!=null&&info.video));
  if(info!=null&&!info.video){
   LinearLayout row=ui.row();final Widgets.Wave w=new Widgets.Wave(this,ui);w.peaks=peaks==null?new float[0]:peaks;final TextView play=roundPlay();row.addView(play);row.addView(w,new LinearLayout.LayoutParams(0,dp(64),1));
   final TextView time=ui.small("0:00 / "+clock(info.duration));
   play.setOnClickListener(new View.OnClickListener(){public void onClick(View v){toggleAudio(source,w,play,time);}});
   w.seek=new Widgets.Wave.Seek(){public void to(float f){if(player!=null)player.seekTo((int)(f*player.getDuration()));else{toggleAudio(source,w,play,time);}}};
   card.addView(row);time.setPadding(dp(62),0,0,0);card.addView(time);if(peaks==null)card.addView(note(t("Ses dalgası hazırlanıyor…","Pêla dengê tê amadekirin…")));
   sourcePos=new java.util.concurrent.Callable<Double>(){public Double call(){return player!=null&&playerFile==source?player.getCurrentPosition()/1000.0:0.0;}};sourceMarks=marksRow(sourcePos);card.addView(sourceMarks);
  }else if(excerpt!=null&&base==null&&info==null&&!paged()&&!ext.equals("image")){
   TextView tx=ui.label(excerpt,13,ui.text,false);tx.setTypeface(Typeface.MONOSPACE);tx.setMaxLines(14);tx.setEllipsize(TextUtils.TruncateAt.END);tx.setPadding(dp(12),dp(10),dp(12),dp(10));tx.setBackground(ui.round(ui.surface2,12,0));card.addView(tx);
  }else if(base==null){
   LinearLayout wait=ui.column();wait.setGravity(Gravity.CENTER);wait.setMinimumHeight(dp(180));wait.setBackground(ui.round(ui.surface2,14,0));wait.addView(ui.badge(iconFor(new ListedFile(source,display,ext,info)),56,ui.accentSoft,ui.accentText));
   TextView l=ui.small(excerpt!=null?excerpt:paged()&&!ext.equals("pdf")?t("Belge sayfaları hazırlanıyor…","Rûpelên belgeyê tên amadekirin…"):t("Önizleme hazırlanıyor…","Pêşdîtin tê amadekirin…"));l.setPadding(0,dp(10),0,0);wait.addView(l);card.addView(wait,new LinearLayout.LayoutParams(-1,dp(200)));
  }else if(info!=null&&info.video&&!marking){
   // The video itself, ready to play, with its controls and the start/end buttons.
   final int[] at=sourceVideoAt;card.addView(player(source,info.shownWidth(),info.shownHeight(),base,false,at));final VideoView own=video;
   sourcePos=new java.util.concurrent.Callable<Double>(){public Double call(){return (own.isPlaying()?own.getCurrentPosition():at[0])/1000.0;}};sourceMarks=marksRow(sourcePos);card.addView(sourceMarks);
  }else{
   FrameLayout holder=new FrameLayout(this);final Widgets.Picture pic=new Widgets.Picture(this,ui);pic.show(base);holder.addView(pic,new FrameLayout.LayoutParams(-1,-2));sourcePicture=pic;
   if(marking){pic.mode=Widgets.Picture.SELECT;pic.regions.addAll(copyRegions(regions));pic.active=pic.regions.size()-1;pic.listener=new Widgets.Picture.Listener(){public void changed(List<double[]> r){regions.clear();regions.addAll(copyRegions(r));preview=null;if(regionNote!=null)regionNote.setText(regionText());}};}
   card.addView(holder);
   if(marking){card.addView(note(ext.equals("pdf")?t("İsteğe bağlı: otomatik bulunamayan filigranın üstünü çerçevele; o alan her sayfada çevresinin rengiyle kapatılır.","Ne mecbûrî: li ser nîşana avê ya ku bixweber nehat dîtin çarçove bike; ew qad li her rûpelê bi rengê derdorê tê girtin."):t("Filigranın ya da logonun üstünü parmağınla çerçevele. Köşelerden boyutlandır, içinden taşı. En fazla 4 alan.","Li ser nîşana avê an logoyê bi tiliya xwe çarçoveyekê xêz bike. Ji goşeyan mezin bike, ji navê bikişîne. Herî zêde 4 qad.")));
    LinearLayout r=ui.row();r.setPadding(0,dp(8),0,0);TextView clear=ui.button(t("Alanları temizle","Qadan paqij bike"),"close",2,new View.OnClickListener(){public void onClick(View v){regions.clear();preview=null;sourceVersion++;build();}});r.addView(clear,ui.weight(1));
    if(info!=null&&info.video){r.addView(new View(this),new LinearLayout.LayoutParams(dp(8),1));TextView next=ui.button(t("Başka kare","Kareke din"),"camera",1,new View.OnClickListener(){public void onClick(View v){double at=frameAt<0?Math.min(1,info.duration*0.1):frameAt;frameAt=(at+Math.max(1,info.duration/6))%Math.max(1,info.duration);loadBase();}});r.addView(next,ui.weight(1));}
    card.addView(r);}
   if(paged()&&pdfCount>0){LinearLayout nav=ui.row();nav.setGravity(Gravity.CENTER);nav.setPadding(0,dp(8),0,0);
    TextView prev=iconButton("chevron_left",new View.OnClickListener(){public void onClick(View v){turnPage(-1);}});TextView nx=iconButton("chevron",new View.OnClickListener(){public void onClick(View v){turnPage(1);}});
    pageLabel=ui.label(pageText(),14,ui.text,true);pageLabel.setPadding(dp(14),0,dp(14),0);nav.addView(prev);nav.addView(pageLabel);nav.addView(nx);card.addView(nav);}
  }
  return card;}
 private String sourceKeyNow(){boolean marking=action.equals("watermark")&&(ext.equals("pdf")||ext.equals("image")||(info!=null&&info.video));
  // Pages and frames change in place with a fade; these are what rebuild the card.
  return source.getAbsolutePath()+"|"+(base!=null)+"|"+marking+"|"+(pdfCount>0)+"|"+(peaks!=null)+"|"+(excerpt==null?0:excerpt.hashCode())+"|"+sourceVersion;}
 private void turnPage(int d){int n=pdfPage+d;if(n<0||n>=pdfCount)return;pdfPage=n;if(pageLabel!=null)pageLabel.setText(pageText());if(preview!=null){preview=null;build();}loadBase();}
 private static List<double[]> copyRegions(List<double[]> in){List<double[]> out=new ArrayList<double[]>();for(double[] r:in)out.add(r.clone());return out;}
 private TextView roundPlay(){TextView p=new TextView(this);p.setCompoundDrawablesRelative(ui.icon("play",ui.onAccent,26),null,null,null);p.setPadding(dp(15),dp(15),dp(15),dp(15));p.setBackground(ui.ripple(ui.round(ui.accent,28,0),28));p.setElevation(dp(3));p.setClickable(true);return p;}
 /** Video with its own controls: play/pause, seek bar and time. The file's own video starts paused on
  *  its first picture; preview clips play straight away and loop. */
 private View player(File f,int w,int h,Bitmap poster,final boolean autoplay){return player(f,w,h,poster,autoplay,new int[1]);}
 /** last[0] keeps the position: Android drops the video when the screen is rebuilt, it comes back there. */
 private View player(File f,int w,int h,Bitmap poster,final boolean autoplay,final int[] last){
  LinearLayout wrap=ui.column();final FrameLayout box=new FrameLayout(this);box.setBackground(ui.round(0xFF000000,14,0));box.setClipToOutline(true);
  int width=getResources().getDisplayMetrics().widthPixels-dp(56);int height=(int)Math.max(dp(200),Math.min(Math.max(dp(420),getResources().getDisplayMetrics().heightPixels*0.6f),(float)width*Math.max(1,h)/Math.max(1,w)));
  video=new VideoView(this);final VideoView v=video;box.addView(v,new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER));
  final ImageView cover=new ImageView(this);cover.setScaleType(ImageView.ScaleType.FIT_CENTER);if(poster!=null&&!autoplay){cover.setImageBitmap(poster);box.addView(cover,new FrameLayout.LayoutParams(-1,-1));}
  wrap.addView(box,new LinearLayout.LayoutParams(-1,height));
  LinearLayout bar=ui.row();bar.setPadding(0,dp(6),0,0);final TextView play=iconButton(autoplay?"pause":"play",null);
  final SeekBar seek=new SeekBar(this);seek.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent));seek.setThumbTintList(android.content.res.ColorStateList.valueOf(ui.accent));
  final TextView time=ui.small("0:00 / 0:00");bar.addView(play);bar.addView(seek,new LinearLayout.LayoutParams(0,-2,1));bar.addView(time);wrap.addView(bar);
  final Runnable[] tick=new Runnable[1];
  final Runnable icon=new Runnable(){public void run(){play.setCompoundDrawablesRelative(ui.icon(v.isPlaying()?"pause":"play",ui.text,24),null,null,null);}};
  play.setOnClickListener(new View.OnClickListener(){public void onClick(View x){if(v.isPlaying()){v.pause();last[0]=v.getCurrentPosition();}else{cover.setVisibility(View.GONE);v.start();handler.post(tick[0]);}icon.run();}});
  v.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer mp){mp.setLooping(autoplay);seek.setMax(Math.max(1,v.getDuration()));
   if(autoplay){v.start();handler.post(tick[0]);}else v.seekTo(Math.max(1,last[0]));icon.run();seek.setProgress(last[0]);time.setText(tclock(last[0]/1000.0)+" / "+clock(v.getDuration()/1000.0));}});
  v.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer mp){icon.run();}});
  v.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer mp,int a,int b){toast(t("Bu video telefonun oynatıcısıyla gösterilemiyor; işlem yine de yapılabilir.","Ev vîdyo bi lîstikvana telefonê nayê nîşandan; kar dîsa jî dibe."));return true;}});
  v.setOnTouchListener(new View.OnTouchListener(){public boolean onTouch(View x,MotionEvent e){if(e.getAction()==MotionEvent.ACTION_UP)play.performClick();return true;}});
  seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
   public void onProgressChanged(SeekBar s,int value,boolean user){if(user){cover.setVisibility(View.GONE);v.seekTo(value);last[0]=value;time.setText(tclock(value/1000.0)+" / "+clock(v.getDuration()/1000.0));}}
   public void onStartTrackingTouch(SeekBar s){s.getParent().requestDisallowInterceptTouchEvent(true);}public void onStopTrackingTouch(SeekBar s){}});
  tick[0]=new Runnable(){public void run(){if(!v.isAttachedToWindow())return;try{int d=Math.max(1,v.getDuration()),pos=v.getCurrentPosition();last[0]=pos;seek.setMax(d);seek.setProgress(pos);time.setText(tclock(pos/1000.0)+" / "+clock(d/1000.0));icon.run();}catch(Exception ignored){}
   if(v.isPlaying())handler.postDelayed(this,200);}};
  v.setVideoPath(f.getAbsolutePath());return wrap;}
 private void toggleAudio(final File f,final Widgets.Wave w,final TextView button,final TextView time){
  try{if(player!=null&&player.isPlaying()){player.pause();button.setCompoundDrawablesRelative(ui.icon("play",ui.onAccent,26),null,null,null);return;}
   if(player==null||playerFile!=f){if(player!=null){try{player.release();}catch(Exception ignored){}}handler.removeCallbacksAndMessages(null);player=new MediaPlayer();player.setDataSource(f.getAbsolutePath());player.prepare();playerFile=f;}
   player.start();button.setCompoundDrawablesRelative(ui.icon("pause",ui.onAccent,26),null,null,null);
   player.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer mp){button.setCompoundDrawablesRelative(ui.icon("play",ui.onAccent,26),null,null,null);w.played=0;w.invalidate();}});
   handler.post(new Runnable(){public void run(){MediaPlayer p=player;if(p==null)return;try{int d=Math.max(1,p.getDuration());w.played=(float)p.getCurrentPosition()/d;w.invalidate();if(time!=null)time.setText(clock(p.getCurrentPosition()/1000.0)+" / "+clock(d/1000.0));if(p.isPlaying())handler.postDelayed(this,120);}catch(Exception ignored){}}});
  }catch(Exception e){toast(t("Bu ses telefonun oynatıcısıyla çalınamıyor.","Ev deng bi lîstikvana telefonê nayê lêdan."));}}
 private File playerFile;
 private void stopMedia(){sourceView=null;previewView=null;sourceKey="";previewKey="";handler.removeCallbacksAndMessages(null);if(video!=null){try{video.stopPlayback();}catch(Exception ignored){}video=null;}if(player!=null){try{player.release();}catch(Exception ignored){}player=null;playerFile=null;}}
 @Override protected void onPause(){super.onPause();if(player!=null&&player.isPlaying())player.pause();if(video!=null&&video.isPlaying())video.pause();}

 // ---- convert: the format ring
 static String[] frontFormats(MediaEngine.Info info,String ext){String[] all=formatValues(info,ext);int n=info!=null&&info.video&&info.audio?6:info!=null&&!info.video?6:ext.equals("pdf")?6:all.length<=8?all.length:6;return Arrays.copyOf(all,Math.min(n,all.length));}
 private View convertCard(){
  LinearLayout card=ui.card();card.setGravity(Gravity.CENTER_HORIZONTAL);LinearLayout.LayoutParams lp=ui.margins(-1,-2,0,14,0,0);card.setLayoutParams(lp);
  final String[] all=formatValues(info,ext),front=frontFormats(info,ext),back=Arrays.copyOfRange(all,front.length,all.length);
  if(!Arrays.asList(all).contains(targetFormat))targetFormat=all[0];
  TextView head=ui.label(t("Neye dönüştürülsün?","Bibe çi formatê?"),17,ui.text,true);head.setLayoutParams(new LinearLayout.LayoutParams(-1,-2));card.addView(head);
  final Widgets.Donut d=new Widgets.Donut(this,ui);d.showBack=donutBack;
  if(back.length>0){card.addView(ui.space(10));card.addView(segmented(new String[]{t("Sık kullanılan ","Yên pir ")+front.length,t("Diğer ","Yên din ")+back.length},donutBack?1:0,new int[]{0,1},new Pick(){public void pick(int i){if((i==1)!=d.showBack){d.showBack=i==1;donutBack=d.showBack;flipAnim=true;build();}}}));}
  String src=info!=null?(info.video?t("video","vîdyo"):t("ses","deng")):ext.equals("image")?t("fotoğraf","wêne"):ext.toUpperCase(Locale.ROOT);
  int count=batchEnabled?files.size():1;d.set(front,back,targetFormat,count+" "+src,"→ "+targetFormat);
  d.listener=new Widgets.Donut.Listener(){public void chosen(String f){if(busy)return;targetFormat=f;preview=null;build();}public void flipped(boolean b){donutBack=b;flipAnim=true;build();}};
  card.addView(d,new LinearLayout.LayoutParams(-1,-2));if(flipAnim){flipAnim=false;d.animateIn();}
  if(back.length>0)card.addView(centered(ui.small(t("Diğer biçimler için ortaya dokun.","Ji bo formatên din li navendê bitikîne."))));
  String f=targetFormat.toLowerCase(Locale.ROOT);LinearLayout opts=ui.column();opts.setLayoutParams(new LinearLayout.LayoutParams(-1,-2));
  if(info!=null&&info.video&&Arrays.asList("mp4","mkv","webm","mov","avi","mpeg","ts").contains(f)){opts.addView(caption(t("Video kalitesi","Kalîteya vîdyoyê")));opts.addView(chips(new String[]{t("Dengeli","Hevseng"),t("Yüksek","Bilind"),t("Küçük dosya","Dosyeya biçûk")},qualityChoice,new Pick(){public void pick(int i){qualityChoice=i;preview=null;build();}}));}
  if(ext.equals("image")){
   if(!f.equals("png")&&!f.equals("bmp")){opts.addView(caption(t("Kalite","Kalîte")));opts.addView(choice("q",new String[]{"1","2","3"},new String[]{t("Yüksek","Bilind"),t("Dengeli","Hevseng"),t("Küçük dosya","Dosyeya biçûk")},"2"));}
   opts.addView(caption(t("Boyut","Mezinahî")));opts.addView(choice("scale",new String[]{"100","75","50","25"},new String[]{"%100","%75","%50","%25"},"100"));
   opts.addView(caption(t("Renk","Reng")));opts.addView(choice("gray",new String[]{"0","1"},new String[]{t("Renkli","Rengîn"),t("Siyah-beyaz","Reş û spî")},"0"));}
  if(ext.equals("pdf")&&(f.equals("png")||f.equals("jpg"))){opts.addView(caption(t("Çözünürlük (her sayfa ayrı resim olur)","Çareserî (her rûpel dibe wêneyek)")));opts.addView(choice("dpi",new String[]{"96","150","300"},new String[]{"96 DPI","150 DPI","300 DPI"},"150"));}
  if(info==null&&!ext.equals("image")&&!ext.equals("srt")&&Arrays.asList("pdf","docx","odt","epub","html").contains(f)){opts.addView(caption(t("Belge içeriği","Naveroka belgeyê")));opts.addView(choice("content",new String[]{"0","1"},new String[]{t("Yalnızca metin","Tenê nivîs"),t("Metin ve resimler","Nivîs û wêne")},"0"));
   opts.addView(note(t("Resimler DOCX, ODT, EPUB, HTML ve PDF'ye aktarılır; yerleşim yeniden düzenlenebilir. PDF kaynaklarında sayfa görüntüleri aktarılır.","Wêne di DOCX, ODT, EPUB, HTML û PDFê de tên veguhestin; rêz dibe ku biguhere. Ji PDFê wêneyên rûpelan tên veguhestin.")));}
  card.addView(opts);return card;}
 private View centered(TextView v){v.setGravity(Gravity.CENTER);v.setLayoutParams(new LinearLayout.LayoutParams(-1,-2));return v;}
 private TextView caption(String s){TextView v=ui.label(s,13.5f,ui.muted,true);v.setPadding(0,dp(14),0,dp(8));return v;}
 private View chips(String[] labels,int selected,final Pick p){Ui.Flow f=ui.flow();for(int i=0;i<labels.length;i++){final int k=i;TextView c=ui.chip(labels[i],i==selected,new View.OnClickListener(){public void onClick(View v){if(!busy)p.pick(k);}});f.addView(c);}return f;}
 /** Chips bound to an option of the current tool. */
 private View choice(final String key,final String[] values,String[] labels,String fallback){String cur=val(key,fallback);int sel=Arrays.asList(values).indexOf(cur);return chips(labels,sel,new Pick(){public void pick(int i){put(key,values[i]);preview=null;build();}});}
 /** On/off chips for independent switches. */
 private View toggles(final String[] keys,String[] labels,String[] defaults){Ui.Flow f=ui.flow();for(int i=0;i<keys.length;i++){final String k=keys[i];final boolean on=val(k,defaults[i]).equals("1");f.addView(ui.chip(labels[i],on,new View.OnClickListener(){public void onClick(View v){if(busy)return;put(k,on?"0":"1");preview=null;build();}}));}return f;}
 private String key(String k){return action+"."+k;}
 private String val(String k,String d){String v=vals.get(key(k));return v==null?d:v;}
 private void put(String k,String v){vals.put(key(k),v);}
 private EditText field(final String k,String label,String fallback,String hint,LinearLayout into){LinearLayout col=ui.column();col.addView(caption(label));final EditText e=ui.input(val(k,fallback),hint,true);e.setEnabled(!busy);fieldViews.put(k,e);
  e.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int b,int c){}public void onTextChanged(CharSequence s,int a,int b,int c){}public void afterTextChanged(Editable s){put(k,s.toString());preview=null;}});col.addView(e);into.addView(col);return e;}
 private void times(LinearLayout into,boolean withEnd){LinearLayout row=ui.row();row.setGravity(Gravity.TOP);LinearLayout a=ui.column(),b=ui.column();field("start",t("Başlangıç","Destpêk"),"0","0:00",a);row.addView(a,ui.weight(1));
  if(withEnd){row.addView(new View(this),new LinearLayout.LayoutParams(dp(10),1));field("end",t("Bitiş · boşsa sona kadar","Dawî · vala be heta dawiyê"),"",t("sona kadar","heta dawiyê"),b);row.addView(b,ui.weight(1));}
  into.addView(row);if(info!=null&&sourcePos!=null)into.addView(marksRow(sourcePos));
  into.addView(note(t("Örnek: 15 = 15 saniye · 1:30 = 1 dakika 30 saniye. Oynatıcıyı istediğin yerde durdurup “bu an” düğmelerine de dokunabilirsin.","Mînak: 15 = 15 çirke · 1:30 = 1 deqe û 30 çirke. Lîstikvanê li cihê xwestî rawestîne û bişkokên “niha” bitikîne.")));}

 // ---- tools
 private View toolGrid(List<String[]> acts){
  LinearLayout grid=ui.column();grid.setPadding(0,dp(14),0,0);LinearLayout row=null;int col=0;
  for(final String[] a:acts){if(a[0].equals("convert"))continue;if(col%3==0){row=ui.row();row.setGravity(Gravity.TOP);grid.addView(row,ui.margins(-1,-2,0,0,0,8));}
   boolean on=a[0].equals(action);LinearLayout tile=ui.column();tile.setGravity(Gravity.CENTER_HORIZONTAL);tile.setPadding(dp(6),dp(12),dp(6),dp(10));tile.setMinimumHeight(dp(104));
   tile.setBackground(ui.ripple(ui.round(on?ui.accentSoft:ui.surface,16,on?ui.accent:ui.border),16));
   FrameLayout b=ui.badge(a[3],40,on?ui.accent:ui.accentSoft,on?ui.onAccent:ui.accentText);tile.addView(b);
   TextView l=ui.label(ku?a[2]:a[1],12.5f,on?ui.accentText:ui.text,on);l.setGravity(Gravity.CENTER);l.setPadding(0,dp(7),0,0);l.setMaxLines(2);tile.addView(l);
   if(NEW.contains(a[0])){TextView tag=ui.label(t("YENİ","NÛ"),9.5f,ui.onAccent,true);tag.setPadding(dp(6),dp(1),dp(6),dp(1));tag.setBackground(ui.round(ui.success,8,0));LinearLayout.LayoutParams tp=ui.margins(-2,-2,0,4,0,0);tile.addView(tag,tp);}
   tile.setOnClickListener(new View.OnClickListener(){public void onClick(View v){chooseTool(a[0]);}});
   row.addView(tile,new LinearLayout.LayoutParams(0,-2,1));if(col%3!=2)row.addView(new View(this),new LinearLayout.LayoutParams(dp(8),1));col++;}
  while(row!=null&&col%3!=0){row.addView(new View(this),new LinearLayout.LayoutParams(0,1,1));if(col%3!=2)row.addView(new View(this),new LinearLayout.LayoutParams(dp(8),1));col++;}
  if(action.length()==0)grid.addView(note(t("Bir araç seç; ayarları burada açılır.","Amûrekê hilbijêre; mîheng li vir vedibin.")));
  return grid;}
 static final Set<String> NEW=new HashSet<String>(Arrays.asList("watermark","denoise","compress","pages","pdf_rotate","edit"));
 private View optionsCard(){
  LinearLayout c=ui.card();c.setTag("options");c.setLayoutParams(ui.margins(-1,-2,0,6,0,0));
  String[] a=label(action);LinearLayout head=ui.row();head.addView(ui.badge(icon(action),36,ui.accentSoft,ui.accentText));TextView title=ui.label(ku?a[1]:a[0],18,ui.text,true);title.setPadding(dp(12),0,0,0);head.addView(title,new LinearLayout.LayoutParams(0,-2,1));c.addView(head);
  boolean video=info!=null&&info.video,pdf=ext.equals("pdf"),image=ext.equals("image");
  if(action.equals("watermark")){
   if(pdf){c.addView(desc(t("Önce otomatik bulunur: filigran olarak işaretlenmiş katmanlar, açıklamalar ve yarı saydam, eğik yazılar. Yazı bilinirse ondan geçen her yazı bloğu silinir. İşe yaramazsa önizlemede alanı çerçevele; o alan çevresinin rengiyle kapatılır.","Pêşî bixweber tê dîtin: qatên wekî nîşana avê, şîrove û nivîsên nîv-zelal û xwar. Ger nivîs were zanîn, her bloka ku wê dihewîne tê jêbirin. Ger nebe, qadê di pêşdîtinê de çarçove bike; ew bi rengê derdorê tê girtin.")));
    c.addView(caption(t("Ne aransın?","Çi bê lêgerîn?")));c.addView(toggles(new String[]{"auto","repeated"},new String[]{t("Otomatik bul","Bixweber bibîne"),t("Her sayfada tekrar eden logo/görseller","Logo/wêneyên ku li her rûpelê dubare dibin")},new String[]{"1","0"}));
    field("keyword",t("Filigrandaki yazı (isteğe bağlı)","Nivîsa nîşana avê (ne mecbûrî)"),"",t("ör. GİZLİ, TASLAK, site adı","mînak: NIHÊNÎ, RECEŞ"),c);
    regionNote=note(regionText());c.addView(regionNote);}
   else{c.addView(desc(video?t("Videonun üstündeki logo, yazı veya filigran kaldırılır. Yukarıdaki karede alanı çerçevele. Doldur: çevredeki görüntüden tamamlar. Bulanıklaştır: alanı okunmaz hâle getirir.","Logo, nivîs an nîşana avê ji vîdyoyê tê rakirin. Li jor qadê çarçove bike. Tije bike: ji wêneyê derdorê temam dike. Şêlû bike: qadê nexwendî dike."):t("Fotoğraftaki logo, tarih veya filigran kaldırılır. Yukarıda alanı çerçevele.","Logo, dîrok an nîşana avê ji wêneyê tê rakirin. Li jor qadê çarçove bike.")));
    c.addView(caption(t("Yöntem","Rêbaz")));c.addView(choice("mode",new String[]{"fill","blur"},new String[]{t("Doldur (çevreden tamamla)","Tije bike (ji derdorê)"),t("Bulanıklaştır","Şêlû bike")},"fill"));
    regionNote=note(regionText());c.addView(regionNote);}}
  else if(action.equals("denoise")){
   c.addView(desc(t("Hışırtı, cızırtı, tıkırtı ve elektrik uğultusu azaltılır; video görüntüsüne dokunulmaz. Önizle ile 10 saniyelik parçayı önce/sonra dinleyebilirsin.","Xişxiş, çirçir, tiqtiq û gimgima elektrîkê kêm dibin; wêneyê vîdyoyê nayê guhertin. Bi Pêşdîtinê 10 çirkeyan berê/paşê guhdarî bike.")));
   c.addView(caption(t("Temizleme gücü","Hêza paqijkirinê")));c.addView(choice("level",new String[]{"1","2","3"},new String[]{t("Hafif","Sivik"),t("Orta","Navîn"),t("Güçlü","Xurt")},"2"));
   c.addView(caption(t("Neler temizlensin?","Çi bê paqijkirin?")));c.addView(toggles(new String[]{"hiss","clicks","hum","voice","loud"},new String[]{t("Hışırtı / arka plan gürültüsü","Xişxiş / dengê paşxanê"),t("Cızırtı ve tıkırtı","Çirçir û tiqtiq"),t("Uğultu (elektrik)","Gimgim (elektrîk)"),t("Konuşmayı netleştir","Axaftinê zelal bike"),t("Ses seviyesini dengele","Asta dengê hevseng bike")},new String[]{"1","1","1","0","1"}));
   field("at",t("Önizleme başlangıcı","Destpêka pêşdîtinê"),"0","0:00",c);}
  else if(action.equals("compress")){
   if(pdf){c.addView(desc(t("PDF'deki büyük resimler yeniden sıkıştırılır; yazılar yazı olarak kalır. Taranmış belgelerde en çok kazanç sağlanır.","Wêneyên mezin ên PDFê ji nû ve têne pêçandin; nivîs wek nivîs dimînin.")));c.addView(caption(t("Sıkıştırma","Pêçandin")));c.addView(choice("level",new String[]{"1","2","3"},new String[]{t("Hafif","Sivik"),t("Dengeli","Hevseng"),t("Güçlü","Xurt")},"2"));}
   else{c.addView(desc(t("Dosya boyutu küçülür. Önizle ile birkaç saniyelik örneği izleyip tahmini boyutu görebilirsin.","Mezinahiya dosyeyê kêm dibe. Bi Pêşdîtinê mînakekê temaşe bike û mezinahiya texmînî bibîne.")));
    c.addView(caption(t("Sıkıştırma","Pêçandin")));c.addView(choice("level",new String[]{"1","2","3"},new String[]{t("Hafif","Sivik"),t("Dengeli","Hevseng"),t("Güçlü","Xurt")},"2"));
    c.addView(caption(t("Çözünürlük","Çareserî")));c.addView(choice("height",new String[]{"0","1080","720","480"},new String[]{t("Aynı","Wek xwe"),"1080p","720p","480p"},"0"));}}
  else if(action.equals("pages")){c.addView(desc(t("Seçtiğin sayfaları yeni PDF'de tut ya da sil. Sırayı değiştirmek için 3,1,2 yaz.","Rûpelên hilbijartî di PDFa nû de bihêle an jê bibe. Ji bo guhertina rêzê 3,1,2 binivîse.")));
   c.addView(caption(t("İşlem","Kar")));c.addView(choice("keep",new String[]{"1","0"},new String[]{t("Seçilenleri tut","Hilbijartiyan bihêle"),t("Seçilenleri sil","Hilbijartiyan jê bibe")},"1"));field("spec",t("Sayfalar","Rûpel")+(pdfCount>0?" (1–"+pdfCount+")":""),"1",t("ör. 1-3, 5, 8-","mînak: 1-3, 5, 8-"),c);}
  else if(action.equals("pdf_rotate")){c.addView(caption(t("Açı","Goşe")));c.addView(choice("angle",new String[]{"90","180","270"},new String[]{"90° ↻","180°","90° ↺"},"90"));field("spec",t("Sayfalar · boşsa hepsi","Rûpel · vala be hemû"),"",t("hepsi","hemû"),c);}
  else if(action.equals("edit")){c.addView(desc(t("Döndür, aynala, boyutunu küçült veya siyah-beyaz yap. Biçim korunur.","Bizivirîne, berevajî bike, biçûk bike an reş û spî bike. Format tê parastin.")));
   c.addView(caption(t("Döndür","Bizivirîne")));c.addView(choice("angle",new String[]{"0","90","180","270"},new String[]{"0°","90° ↻","180°","90° ↺"},"0"));
   c.addView(caption(t("Boyut","Mezinahî")));c.addView(choice("scale",new String[]{"100","75","50","25"},new String[]{"%100","%75","%50","%25"},"100"));
   c.addView(caption(t("Diğer","Yên din")));c.addView(toggles(new String[]{"flip","gray"},new String[]{t("Aynala","Berevajî bike"),t("Siyah-beyaz","Reş û spî")},new String[]{"0","0"}));}
  else if(action.equals("subtitle")){c.addView(desc(t("SRT, ASS veya VTT altyazıyı videoya ekler; sonuç MP4 olur. Kalıcı seçenekte yazı görüntüye işlenir. Açılıp kapatılabilir seçenek çok hızlıdır.","Binnivîsa SRT, ASS an VTT li vîdyoyê zêde dike; encam MP4 e. Mayînde li ser wêneyê tê nivîsandin. Vekirin/girtin pir bilez e.")));
   c.addView(otherPicker(t("Altyazı dosyasını seç","Pela binnivîsê hilbijêre")));c.addView(caption(t("Nasıl eklensin?","Çawa bê zêdekirin?")));c.addView(choice("subMode",new String[]{"burn","soft"},new String[]{t("Kalıcı (görüntüye yazılır)","Mayînde (li ser wêneyê)"),t("Açılıp kapatılabilir","Vekirin/girtin dibe")},"burn"));}
  else if(action.equals("ocr")){c.addView(desc(t("Taranmış sayfa veya fotoğraftaki yazı okunur. OCR hataları olabilir.","Nivîsa rûpela skankirî an wêneyê tê xwendin. Dibe ku çewtî hebin.")));
   c.addView(caption(t("Çıktı biçimi","Formata encamê")));c.addView(choice("format",new String[]{"PDF","TXT","DOCX","ODT","RTF","EPUB","MD","HTML"},new String[]{"PDF","TXT","DOCX","ODT","RTF","EPUB","MD","HTML"},"PDF"));
   c.addView(caption(t("Yazının dili","Zimanê nivîsê")));c.addView(choice("lang",new String[]{"tur+eng","tur","eng","kmr","ara","fas"},new String[]{"Türkçe + English","Türkçe","English","Kurmancî","العربية","فارسی"},"tur+eng"));}
  else if(action.equals("transcribe")){c.addView(desc(t("TXT düz metin veya SRT altyazı. Zamanlar konuşma parçalarına göredir. Müzik ve gürültü tanımayı etkileyebilir.","TXT nivîsa sade an SRT binivîs. Dem li gor parçeyên axaftinê ne. Muzîk û deng dikarin bandor bikin.")));
   c.addView(caption(t("Çıktı","Encam")));c.addView(choice("speechOut",new String[]{"TXT","SRT"},new String[]{"TXT","SRT"},"TXT"));c.addView(caption(t("Konuşmanın dili","Zimanê axaftinê")));c.addView(choice("speechLang",new String[]{"tr","en"},new String[]{"Türkçe","English"},"tr"));times(c,true);}
  else if(action.equals("subtitle_text")||action.equals("subtitle_restore")){c.addView(desc(t("Çeviri ayrı programda yapılır. Her altyazıyı tek satırda tut; satır sayısını ve sırasını koru. TXT → SRT için zamanlar orijinal SRT'den alınır.","Di bernameyeke din de wergerîne. Her binivîsê di rêzekê de bihêle; hejmar û rêza rêzan biparêze.")));if(action.equals("subtitle_restore"))c.addView(otherPicker(t("Orijinal SRT dosyasını seç","SRT ya orîjînal hilbijêre")));}
  else if(action.equals("split")&&info==null){field("pdfPart",t("Her dosyada kaç sayfa olsun?","Di her dosyeyê de çend rûpel?"),"1","1",c);}
  else if(action.equals("merge")){c.addView(desc(image?t("Fotoğraflar sırayla tek PDF'de birleşir. Listedeki bütün fotoğraflar için aşağıdaki kutuyu işaretle.","Wêne bi rêzê di PDFekê de yek dibin. Ji bo hemû wêneyên lîsteyê qutiya jêrîn nîşan bike."):t("Seçili dosyanın arkasına ikinci dosya eklenir. Listedeki hepsini birleştirmek için aşağıdaki kutuyu işaretle.","Dosyeya duyem li pey a hilbijartî tê zêdekirin. Ji bo hemûyan qutiya jêrîn nîşan bike.")));c.addView(otherPicker(t("Arkasına eklenecek dosyayı seç","Dosyeya ku li pey wê were hilbijêre")));}
  else if(Arrays.asList("add","replace").contains(action)){c.addView(otherPicker(t("Eklenecek ses dosyasını seç","Dosyeya deng hilbijêre")));c.addView(desc(t("Sesin videoda başlayacağı ve biteceği zaman:","Dema destpêk û dawiya deng di vîdyoyê de:")));times(c,true);
   LinearLayout r=ui.row();LinearLayout a1=ui.column(),b1=ui.column();field("audioStart",t("Ses dosyasında başlangıç","Destpêka deng"),"0","0:00",a1);field("audioEnd",t("Ses dosyasında bitiş","Dawiya deng"),"",t("sona kadar","heta dawiyê"),b1);r.addView(a1,ui.weight(1));r.addView(new View(this),new LinearLayout.LayoutParams(dp(10),1));r.addView(b1,ui.weight(1));c.addView(r);}
  else if(action.equals("mute")){c.addView(desc(t("Videonun bütün sesi kaldırılır.","Hemû dengê vîdyoyê tê rakirin.")));}
  else if(info!=null){String hint=action.equals("trim")?t("Başlangıç ve bitiş arası ayrı bir dosyaya kaydedilir.","Navbera destpêk û dawiyê di dosyeyeke nû de tomar dibe."):action.equals("remove")?t("Seçtiğin bölüm silinir, kalanlar birleştirilir.","Beşa hilbijartî tê rakirin, yên mayî yek dibin."):t("İşlemin uygulanacağı zaman aralığı:","Navbera demê ya karê:");
   c.addView(desc(hint));times(c,!action.equals("frame"));
   if(action.equals("split"))field("part",t("Her parça kaç saniye olsun?","Her parçe çend çirke?"),"60","60",c);
   if(action.equals("rotate")){c.addView(caption(t("Açı","Goşe")));c.addView(choice("factor",new String[]{"90","180","270"},new String[]{"90° ↻","180°","90° ↺"},"90"));}
   if(action.equals("speed")){c.addView(caption(t("Hız","Lez")));c.addView(choice("factor",new String[]{"0.5","0.75","1.25","1.5","2"},new String[]{"0.5×","0.75×","1.25×","1.5×","2×"},"1.5"));}
   if(action.equals("volume")){c.addView(caption(t("Ses düzeyi","Asta dengê")));c.addView(choice("factor",new String[]{"0.25","0.5","0.75","1.5","2","3"},new String[]{"%25","%50","%75","%150","%200","%300"},"1.5"));}}
  return c;}
 private TextView regionNote;
 private String regionText(){if(ext.equals("pdf"))return regions.isEmpty()?t("Alan seçilmedi (isteğe bağlı).","Qad nehatiye hilbijartin (ne mecbûrî)."):t("Seçili alan: ","Qadên hilbijartî: ")+regions.size()+t(" · her sayfada kapatılır"," · li her rûpelê tê girtin");
  return regions.isEmpty()?t("Henüz alan seçilmedi.","Hîn qad nehatiye hilbijartin."):"✓ "+t("Seçili alan: ","Qadên hilbijartî: ")+regions.size();}
 private TextView desc(String s){TextView v=ui.body(s);v.setPadding(0,dp(10),0,0);return v;}
 private View otherPicker(String label){LinearLayout col=ui.column();col.setPadding(0,dp(12),0,0);TextView b=ui.button(other==null?label:t("Değiştir: ","Biguherîne: ")+otherDisplay,"folder",1,new View.OnClickListener(){public void onClick(View v){if(!busy)choose(2);}});col.addView(b);
  if(other!=null)col.addView(note("✓ "+otherDisplay));return col;}

 /** Status, progress and the stop button. */
 private void statusCard(LinearLayout into,boolean always){if(!busy&&!always&&ready&&homeNotice==null)return;if(!always&&!busy&&homeNotice!=null)lastStatus=homeNotice;
  LinearLayout c=ui.column();c.setPadding(dp(4),dp(12),dp(4),0);
  status=ui.label(lastStatus.length()==0?(ready?t("Hazır.","Amade ye."):t("Yerel motor hazırlanıyor…","Motora herêmî tê amadekirin…")):lastStatus,14,ui.text,false);c.addView(status);
  if(busy){LinearLayout r=ui.row();r.setPadding(0,dp(8),0,0);progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(1000);progress.setIndeterminate(progressTotal<=0);progress.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent));progress.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(ui.accent));
   r.addView(progress,new LinearLayout.LayoutParams(0,-2,1));percent=ui.small("");percent.setPadding(dp(10),0,0,0);r.addView(percent);c.addView(r);
   TextView stop=ui.button(t("Durdur","Rawestîne"),"stop",3,new View.OnClickListener(){public void onClick(View v){cancel();}});LinearLayout.LayoutParams lp=ui.margins(-1,-2,0,10,0,0);c.addView(stop,lp);}
  into.addView(c);}
 private View resultCard(){LinearLayout c=ui.card();c.setLayoutParams(ui.margins(-1,-2,0,14,0,0));LinearLayout head=ui.row();head.addView(ui.badge("check",40,ui.blend(ui.success,ui.surface,0.8f),ui.success));
  TextView s=ui.label(lastSummary,15,ui.text,true);s.setPadding(dp(12),0,0,0);head.addView(s,new LinearLayout.LayoutParams(0,-2,1));c.addView(head);
  if(!lastOutputs.isEmpty()){LinearLayout r=ui.row();r.setPadding(0,dp(12),0,0);TextView open=ui.button(t("Aç","Veke"),"open",1,new View.OnClickListener(){public void onClick(View v){open(lastOutputs.get(0),lastMimes.get(0));}});
   TextView share=ui.button(t("Paylaş","Parve bike"),"share",1,new View.OnClickListener(){public void onClick(View v){share(lastOutputs,lastMimes);}});r.addView(open,ui.weight(1));r.addView(new View(this),new LinearLayout.LayoutParams(dp(10),1));r.addView(share,ui.weight(1));c.addView(r);}
  return c;}

 // ---- preview result
 private View previewCard(){final Preview p=preview;LinearLayout c=ui.card();c.setTag("preview");c.setLayoutParams(ui.margins(-1,-2,0,14,0,0));
  LinearLayout head=ui.row();head.addView(ui.label(t("Önizleme","Pêşdîtin"),17,ui.text,true),new LinearLayout.LayoutParams(0,-2,1));head.addView(iconButton("close",new View.OnClickListener(){public void onClick(View v){preview=null;build();}}));c.addView(head);
  if(p.kind.equals("compare")){Widgets.Picture pic=new Widgets.Picture(this,ui);pic.compare(p.before,p.after,t("Önce","Berê"),t("Sonra","Paşê"));c.addView(pic,new LinearLayout.LayoutParams(-1,-2));c.addView(note(t("Çizgiyi sürükleyerek karşılaştır.","Xetê bikişîne û berhev bike.")));
   if(p.result!=null&&isVideo(p.result)){TextView play=ui.button(t("Videoyu oynat","Vîdyoyê bilîze"),"play",1,new View.OnClickListener(){public void onClick(View v){p.kind="video";build();}});LinearLayout.LayoutParams lp=ui.margins(-1,-2,0,10,0,0);c.addView(play,lp);}}
  else if(p.kind.equals("video")){if(p.original!=null)c.addView(segmented(new String[]{t("Orijinal","Resen"),t("Sonuç","Encam")},p.showResult?1:0,new int[]{0,1},new Pick(){public void pick(int i){p.showResult=i==1;build();}}));c.addView(ui.space(10));
   MediaEngine.Info shape=info;c.addView(player(p.showResult||p.original==null?p.result:p.original,shape==null?16:shape.shownWidth(),shape==null?9:shape.shownHeight(),null,true));}
  else if(p.kind.equals("audio")){if(p.original!=null)c.addView(segmented(new String[]{t("Orijinal","Resen"),t("Sonuç","Encam")},p.showResult?1:0,new int[]{0,1},new Pick(){public void pick(int i){p.showResult=i==1;build();}}));
   final File f=p.showResult||p.original==null?p.result:p.original;final Widgets.Wave w=new Widgets.Wave(this,ui);w.peaks=p.showResult||p.original==null?p.peaksB:p.peaksA;if(w.peaks==null)w.peaks=new float[0];
   LinearLayout row=ui.row();row.setPadding(0,dp(10),0,0);final TextView play=roundPlay();row.addView(play);row.addView(w,new LinearLayout.LayoutParams(0,dp(64),1));c.addView(row);final TextView time=ui.small("");time.setPadding(dp(62),0,0,0);c.addView(time);
   play.setOnClickListener(new View.OnClickListener(){public void onClick(View v){toggleAudio(f,w,play,time);}});w.seek=new Widgets.Wave.Seek(){public void to(float x){if(player!=null)player.seekTo((int)(x*player.getDuration()));}};}
  else if(p.kind.equals("image")){Widgets.Picture pic=new Widgets.Picture(this,ui);pic.show(p.after);c.addView(pic,new LinearLayout.LayoutParams(-1,-2));}
  else if(p.kind.equals("gif")){ImageView iv=new ImageView(this);iv.setAdjustViewBounds(true);try{Drawable d=ImageDecoder.decodeDrawable(ImageDecoder.createSource(p.result));iv.setImageDrawable(d);if(d instanceof AnimatedImageDrawable)((AnimatedImageDrawable)d).start();}catch(Exception e){iv.setImageBitmap(BitmapFactory.decodeFile(p.result.getAbsolutePath()));}c.addView(iv,new LinearLayout.LayoutParams(-1,-2));}
  else if(p.kind.equals("thumbs")){HorizontalScrollView hs=new HorizontalScrollView(this);hs.setHorizontalScrollBarEnabled(false);LinearLayout strip=ui.row();strip.setGravity(Gravity.TOP);
   for(int i=0;i<p.thumbs.size();i++){LinearLayout cell=ui.column();cell.setPadding(0,0,dp(10),0);ImageView iv=new ImageView(this);iv.setImageBitmap(p.thumbs.get(i));iv.setAdjustViewBounds(true);iv.setScaleType(ImageView.ScaleType.FIT_CENTER);iv.setBackground(ui.round(ui.surface2,10,ui.border));iv.setClipToOutline(true);
    cell.addView(iv,new LinearLayout.LayoutParams(-2,dp(150)));TextView cap=ui.small(i<p.captions.size()?p.captions.get(i):"");cap.setPadding(0,dp(4),0,0);cell.addView(cap);strip.addView(cell);}
   hs.addView(strip);c.addView(hs);}
  else if(p.kind.equals("text")){TextView tx=ui.label(p.text,13,ui.text,false);tx.setTextIsSelectable(true);tx.setPadding(dp(12),dp(10),dp(12),dp(10));tx.setBackground(ui.round(ui.surface2,12,0));c.addView(tx);}
  if(p.note!=null){TextView n=ui.label(p.note,13.5f,ui.text,false);n.setPadding(0,dp(10),0,0);c.addView(n);}
  return c;}
 static boolean isVideo(File f){String n=f.getName().toLowerCase(Locale.ROOT);for(String e:new String[]{".mp4",".mkv",".webm",".mov",".avi",".mpeg",".ts"})if(n.endsWith(e))return true;return false;}
 static boolean isAudio(File f){String n=f.getName().toLowerCase(Locale.ROOT);for(String e:new String[]{".mp3",".wav",".flac",".ogg",".opus",".m4a",".aac",".aiff",".wma"})if(n.endsWith(e))return true;return false;}
 private boolean previewable(String a){if(a.length()==0||a.equals("transcribe")||a.equals("subtitle_text")||a.equals("subtitle_restore"))return false;if(Arrays.asList("add","replace","subtitle").contains(a)&&other==null)return false;if(a.equals("merge")&&other==null)return false;return true;}

 // ---- history and settings
 private JSONArray history(){try{return new JSONArray(getPreferences(0).getString("history","[]"));}catch(Exception e){return new JSONArray();}}
 private void remember(String name,Uri uri,String mime,String act){try{JSONArray h=history(),out=new JSONArray();JSONObject o=new JSONObject();o.put("name",name);o.put("uri",uri.toString());o.put("mime",mime);o.put("action",act);o.put("time",System.currentTimeMillis());
   if(publishingThumb!=null&&publishingThumb.isFile()){File dir=new File(getFilesDir(),"thumbs");dir.mkdirs();File keep=new File(dir,System.nanoTime()+".jpg");Tools.copy(publishingThumb,keep);o.put("thumb",keep.getAbsolutePath());}
   out.put(o);for(int i=0;i<h.length()&&out.length()<60;i++)out.put(h.get(i));for(int i=59;i<h.length();i++){String th=h.optJSONObject(i).optString("thumb","");if(th.length()>0)new File(th).delete();}getPreferences(0).edit().putString("history",out.toString()).apply();}catch(Exception ignored){}}
 private void buildHistory(){page.addView(ui.title(t("Geçmiş","Dîrok")));JSONArray h=history();
  if(h.length()==0){page.addView(ui.space(16));page.addView(ui.body(t("Henüz dönüştürme yok. Dönüştürdüğün dosyalar burada listelenir; dokununca açılır.","Hîn veguherîn tune. Dosyeyên ku tu diguherînî li vir xuya dibin.")));return;}
  LinearLayout head=ui.row();head.addView(ui.small(h.length()+t(" dosya"," dosye")),new LinearLayout.LayoutParams(0,-2,1));TextView clear=ui.button(t("Geçmişi temizle","Dîrokê paqij bike"),null,2,new View.OnClickListener(){public void onClick(View v){JSONArray all=history();for(int i=0;i<all.length();i++){String th=all.optJSONObject(i).optString("thumb","");if(th.length()>0)new File(th).delete();}getPreferences(0).edit().remove("history").apply();build();}});clear.setMinHeight(0);clear.setTextSize(13);clear.setPadding(dp(14),dp(6),dp(14),dp(6));head.addView(clear);page.addView(head);page.addView(ui.space(8));
  for(int i=0;i<h.length();i++)page.addView(historyRow(h.optJSONObject(i)));
  page.addView(note(t("Geçmişten silmek dosyayı silmez.","Jêbirina ji dîrokê dosyeyê jê nabe.")));}
 private View historyRow(final JSONObject o){LinearLayout row=ui.row();row.setPadding(dp(10),dp(10),dp(6),dp(10));row.setBackground(ui.ripple(ui.round(ui.surface,16,ui.border),16));row.setLayoutParams(ui.margins(-1,-2,0,0,0,8));
  String mime=o.optString("mime","");String th=o.optString("thumb","");row.addView(thumb(th.length()>0?new File(th):null,mime.startsWith("video")?"video":mime.startsWith("audio")?"audio":mime.startsWith("image")?"image":"doc",48));
  LinearLayout col=ui.column();col.setPadding(dp(12),0,dp(4),0);TextView n=ui.label(o.optString("name"),14.5f,ui.text,true);n.setSingleLine(true);n.setEllipsize(TextUtils.TruncateAt.MIDDLE);col.addView(n);
  String[] l=label(o.optString("action"));col.addView(ui.small((ku?l[1]:l[0])+" · "+android.text.format.DateUtils.getRelativeTimeSpanString(o.optLong("time"),System.currentTimeMillis(),android.text.format.DateUtils.MINUTE_IN_MILLIS)));row.addView(col,new LinearLayout.LayoutParams(0,-2,1));
  row.addView(iconButton("share",new View.OnClickListener(){public void onClick(View v){share(Arrays.asList(Uri.parse(o.optString("uri"))),Arrays.asList(o.optString("mime")));}}));
  row.setOnClickListener(new View.OnClickListener(){public void onClick(View v){open(Uri.parse(o.optString("uri")),o.optString("mime"));}});return row;}
 /** Results open in the app's own quick viewer; from there "Başka uygulamayla aç" offers the others. */
 private void open(Uri uri,String mime){try{Intent q=new Intent(this,QuickView.class);q.setAction(Intent.ACTION_VIEW);q.setDataAndType(uri,mime);q.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(q);return;}catch(Exception ignored){}
  try{Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(i);}catch(Exception e){toast(t("Bu dosyayı açabilecek uygulama bulunamadı veya dosya taşınmış.","Sepana ku vê dosyeyê veke nehat dîtin an dosye hatiye guhestin."));}}
 private void share(List<Uri> uris,List<String> mimes){try{Intent i;if(uris.size()==1){i=new Intent(Intent.ACTION_SEND);i.setType(mimes.get(0));i.putExtra(Intent.EXTRA_STREAM,uris.get(0));}else{i=new Intent(Intent.ACTION_SEND_MULTIPLE);i.setType("*/*");i.putParcelableArrayListExtra(Intent.EXTRA_STREAM,new ArrayList<Uri>(uris));}
  i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,t("Paylaş","Parve bike")));}catch(Exception e){toast(t("Paylaşılamadı.","Nehat parvekirin."));}}
 private void toast(final String s){runOnUiThread(new Runnable(){public void run(){Toast.makeText(MainActivity.this,s,Toast.LENGTH_LONG).show();}});}
 private void buildSettings(){page.addView(ui.title(t("Ayarlar","Mîheng")));
  LinearLayout lang=ui.card();lang.setLayoutParams(ui.margins(-1,-2,0,14,0,0));lang.addView(settingHead("translate",t("Dil","Ziman")));lang.addView(chips(new String[]{"Türkçe","Kurmancî"},ku?1:0,new Pick(){public void pick(int i){if(busy)return;ku=i==1;getPreferences(0).edit().putBoolean("ku",ku).apply();build();}}));page.addView(lang);
  LinearLayout look=ui.card();look.setLayoutParams(ui.margins(-1,-2,0,12,0,0));look.addView(settingHead("palette",t("Görünüm","Xuyang")));final String[] modes={"system","light","dark"};
  look.addView(chips(new String[]{t("Sistem","Pergal"),t("Aydınlık","Ronî"),t("Karanlık","Tarî")},Arrays.asList(modes).indexOf(themeMode),new Pick(){public void pick(int i){if(busy)return;themeMode=modes[i];getPreferences(0).edit().putString("theme",themeMode).apply();palette();build();}}));
  look.addView(caption(t("Vurgu rengi","Rengê sereke")));LinearLayout sw=ui.row();String[] names={t("Lavanta","Lavanta"),t("Okyanus","Okyanûs"),t("Zümrüt","Zimrût"),t("Mercan","Mercan"),t("Gül","Gul")};
  for(int i=0;i<Ui.ACCENTS.length;i++){final int k=i;FrameLayout dot=new FrameLayout(this);int col=0xFF000000|Ui.ACCENTS[i][dark?1:0];GradientDrawable g=new GradientDrawable();g.setShape(GradientDrawable.OVAL);g.setColor(col);if(i==accentIndex)g.setStroke(dp(3),ui.text);dot.setBackground(g);dot.setContentDescription(names[i]);
   if(i==accentIndex){ImageView ck=new ImageView(this);ck.setImageDrawable(ui.icon("check",0xFFFFFFFF,20));dot.addView(ck,new FrameLayout.LayoutParams(dp(20),dp(20),Gravity.CENTER));}
   dot.setOnClickListener(new View.OnClickListener(){public void onClick(View v){accentIndex=k;getPreferences(0).edit().putInt("accent",k).apply();palette();build();}});LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(dp(40),dp(40));lp.setMargins(0,0,dp(12),0);sw.addView(dot,lp);}
  look.addView(sw);page.addView(look);
  LinearLayout out=ui.card();out.setLayoutParams(ui.margins(-1,-2,0,12,0,0));out.addView(settingHead("folder",t("Kayıt klasörü","Peldanka tomarkirinê")));out.addView(ui.body(outputTree==null?t("Henüz seçilmedi. İlk işlemde sorulur.","Hîn nehatiye hilbijartin. Di karê yekem de tê pirsîn."):folderName(outputTree)));
  TextView change=ui.button(outputTree==null?t("Klasör seç","Peldankê hilbijêre"):t("Değiştir","Biguherîne"),"folder",1,new View.OnClickListener(){public void onClick(View v){pickOutput();}});LinearLayout.LayoutParams lp=ui.margins(-1,-2,0,10,0,0);out.addView(change,lp);page.addView(out);
  LinearLayout about=ui.card();about.setLayoutParams(ui.margins(-1,-2,0,12,0,0));about.addView(settingHead("lock",t("Gizlilik ve sürüm","Nepenî û guherto")));
  about.addView(ui.body(t("Çevrimdışı çalışır. İnternet izni yoktur. Dosyalar hiçbir yere yüklenmez; orijinaller değiştirilmez.","Bê înternetê dixebite. Destûra înternetê tune ye. Dosye li tu derê nayên barkirin; yên resen nayên guhertin.")));
  about.addView(note("Android "+VERSION));TextView scope=ui.button(t("Bu sürümün kapsamı","Taybetiyên vê guhertoyê"),"info",2,new View.OnClickListener(){public void onClick(View v){scope();}});LinearLayout.LayoutParams lp2=ui.margins(-1,-2,0,10,0,0);about.addView(scope,lp2);page.addView(about);}
 private View settingHead(String icon,String s){LinearLayout r=ui.row();r.setPadding(0,0,0,dp(10));r.addView(ui.badge(icon,32,ui.accentSoft,ui.accentText));TextView l=ui.label(s,16,ui.text,true);l.setPadding(dp(10),0,0,0);r.addView(l);return r;}
 private String folderName(Uri tree){try{String id=DocumentsContract.getTreeDocumentId(tree);int c=id.indexOf(':');String path=c>=0?id.substring(c+1):id;return path.length()==0?t("Dahili depolama","Bîra hundirîn"):path;}catch(Exception e){return tree.toString();}}
 private void pickOutput(){Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);startActivityForResult(intent,3);}
 private void scope(){new AlertDialog.Builder(this).setTitle(t("Android sürümü ","Guhertoya Android ")+VERSION).setMessage(t(
  "• Video/ses dönüştürme ve düzenleme; işlemlerden önce önizleme (kısa örnek, önce/sonra karşılaştırma)\n• Video, fotoğraf ve PDF'den filigran/logo silme\n• Seste hışırtı, cızırtı, tıkırtı ve uğultu temizleme\n• Video ve PDF küçültme; PDF sayfa seçme, silme, sıralama ve döndürme\n• Fotoğraf dönüştürme (JPG, PNG, WEBP, BMP, PDF), döndürme ve boyutlandırma; fotoğraflardan PDF; PDF'den resim\n• Belgeler, OCR ve konuşmayı yazıya dökme\n\nFiligran silme her dosyada kusursuz değildir: PDF'de filigran ayrı bir katman veya yazı değilse alan kapatılır; videoda çevreden tamamlama izi kalabilir. OCR ve konuşma tanımada hatalar olabilir. Uzun işlemlerde uygulamayı açık tut.",
  "• Veguherandin û sererastkirina vîdyo/deng; pêşdîtin berî karê (mînaka kurt, berhevkirina berê/paşê)\n• Rakirina nîşana avê/logoyê ji vîdyo, wêne û PDFê\n• Paqijkirina xişxiş, çirçir, tiqtiq û gimgimê ji deng\n• Biçûkkirina vîdyo û PDFê; hilbijartin, jêbirin, rêzkirin û zivirandina rûpelên PDFê\n• Veguherandina wêneyan (JPG, PNG, WEBP, BMP, PDF), zivirandin û mezinahî; PDF ji wêneyan; wêne ji PDFê\n• Belge, OCR û nivîsandina axaftinê\n\nRakirina nîşana avê her car bêkêmasî nîne. Di OCR û nasîna axaftinê de çewtî dikarin hebin. Di karên dirêj de sepanê vekirî bihêle.")).setPositiveButton(t("Tamam","Temam"),null).show();}

 // =====================================================================================
 // Operations
 // =====================================================================================
 static String[] label(String id){
  switch(id){
   case "convert":return new String[]{"Biçimini dönüştür","Formatê biguherîne"};case "watermark":return new String[]{"Filigran / logo sil","Nîşana avê rake"};case "denoise":return new String[]{"Sesi temizle","Dengê paqij bike"};
   case "compress":return new String[]{"Boyutu küçült","Biçûk bike"};case "pages":return new String[]{"Sayfa seç / sil / sırala","Rûpel hilbijêre / jê bibe"};case "pdf_rotate":return new String[]{"Sayfaları döndür","Rûpelan bizivirîne"};case "edit":return new String[]{"Döndür / boyutlandır","Bizivirîne / mezinahî"};
   case "trim":return new String[]{"Kes","Bibire"};case "remove":return new String[]{"Bölüm sil","Beşekê rake"};case "split":return new String[]{"Parçala","Parçe bike"};case "merge":return new String[]{"Birleştir","Yek bike"};
   case "transcribe":return new String[]{"Konuşmayı yazıya dök","Axaftinê bike nivîs"};case "mute_range":return new String[]{"Bölümün sesini kapat","Dengê beşekê bigire"};case "mute":return new String[]{"Sessiz yap","Bêdeng bike"};
   case "extract":return new String[]{"Sesi çıkar · MP3","Deng derxe · MP3"};case "add":return new String[]{"Ses ekle","Deng zêde bike"};case "replace":return new String[]{"Sesi değiştir","Deng biguherîne"};case "frame":return new String[]{"Fotoğraf al","Wêne bistîne"};
   case "gif":return new String[]{"GIF oluştur","GIF çêke"};case "subtitle":return new String[]{"Altyazı ekle","Binnivîs zêde bike"};case "rotate":return new String[]{"Döndür","Bizivirîne"};case "volume":return new String[]{"Ses düzeyi","Asta dengê"};
   case "fade_in":return new String[]{"Yavaşça yükselt","Hêdî bilind bike"};case "fade_out":return new String[]{"Yavaşça azalt","Hêdî kêm bike"};case "speed":return new String[]{"Hızı değiştir","Lezê biguherîne"};
   case "subtitle_text":return new String[]{"SRT → TXT (çeviri için)","SRT → TXT (ji bo wergerê)"};case "subtitle_restore":return new String[]{"Çevrilmiş TXT → SRT","TXT ya wergerandî → SRT"};case "ocr":return new String[]{"OCR ile metni çıkar","Bi OCRê nivîsê derxe"};
   default:return new String[]{id,id};}}
 static String icon(String id){switch(id){case "watermark":return "wand";case "denoise":return "wave";case "compress":return "compress";case "pages":return "pages";case "pdf_rotate":case "rotate":case "edit":return "rotate";case "trim":return "cut";case "remove":return "delete";case "split":return "split";case "merge":return "merge";
  case "transcribe":return "mic";case "mute_range":case "mute":return "mute";case "extract":return "audio";case "add":case "replace":return "volume";case "frame":return "camera";case "gif":return "gif";case "subtitle":case "subtitle_text":case "subtitle_restore":return "subtitles";case "volume":case "fade_in":case "fade_out":return "volume";case "speed":return "speed";case "ocr":return "text";default:return "doc";}}
 /** Output formats offered for a file. */
 static String[] formatValues(MediaEngine.Info info,String ext){
  if(info==null){if(ext.equals("srt"))return new String[]{"TXT"};if(ext.equals("image"))return new String[]{"JPG","PNG","WEBP","PDF","BMP"};if(ext.equals("pdf"))return new String[]{"DOCX","TXT","PNG","JPG","EPUB","HTML","PDF","ODT","RTF","MD"};return new String[]{"PDF","DOCX","TXT","ODT","EPUB","HTML","RTF","MD"};}
  if(info.video&&!info.audio)return new String[]{"MP4","MKV","WEBM","MOV","GIF","AVI","MPEG","TS"};
  if(info.video)return new String[]{"MP4","MKV","WEBM","MOV","GIF","MP3","AVI","MPEG","TS","WAV","FLAC","OGG","OPUS","M4A","AAC","AIFF","WMA"};
  return new String[]{"MP3","WAV","FLAC","M4A","OGG","OPUS","AAC","AIFF","WMA"};}
 /** Operations offered for a file: {id, Turkish, Kurmanji, icon}. Used by the screen and the full self test. */
 static List<String[]> offeredActions(MediaEngine.Info info,String ext){List<String> ids=new ArrayList<String>();
  if(info!=null){boolean v=info.video;ids.add("convert");
   if(v){ids.add("watermark");if(info.audio)ids.add("denoise");ids.add("compress");ids.addAll(Arrays.asList("trim","remove","split","merge","rotate","speed","mute"));if(info.audio)ids.addAll(Arrays.asList("mute_range","extract"));ids.add("add");if(info.audio)ids.add("replace");ids.addAll(Arrays.asList("frame","gif","subtitle"));if(info.audio)ids.add("transcribe");}
   else ids.addAll(Arrays.asList("denoise","trim","remove","split","merge","volume","fade_in","fade_out","mute_range","speed","transcribe"));}
  else if(ext.equals("srt"))ids.addAll(Arrays.asList("convert","subtitle_text"));
  else if(ext.equals("txt"))ids.addAll(Arrays.asList("convert","subtitle_restore"));
  else if(ext.equals("pdf"))ids.addAll(Arrays.asList("convert","watermark","compress","pages","pdf_rotate","split","merge","ocr"));
  else if(ext.equals("image"))ids.addAll(Arrays.asList("convert","watermark","edit","merge","ocr"));
  else ids.add("convert");
  List<String[]> out=new ArrayList<String[]>();for(String id:ids){String[] l=label(id);if(info!=null&&id.equals("trim"))l=info.video?new String[]{"Video kes","Vîdyoyê bibire"}:new String[]{"Ses kes","Dengê bibire"};if(id.equals("compress"))l=ext.equals("pdf")?new String[]{"PDF'yi küçült","PDFê biçûk bike"}:new String[]{"Videoyu küçült","Vîdyoyê biçûk bike"};if(id.equals("merge")&&ext.equals("image"))l=new String[]{"Fotoğraflardan PDF","PDF ji wêneyan"};out.add(new String[]{id,l[0],l[1],icon(id)});}
  return out;}
 private boolean supportsEntry(ListedFile file,String action,String format){boolean media=file.info!=null,video=media&&file.info.video,audio=media&&file.info.audio;boolean pdf=file.ext.equals("pdf"),image=file.ext.equals("image");
  if(action.equals("subtitle_text"))return file.ext.equals("srt");if(action.equals("subtitle_restore"))return file.ext.equals("txt");if(action.equals("transcribe"))return audio;if(action.equals("ocr"))return pdf||image;
  if(action.equals("watermark"))return video||pdf||image;if(action.equals("compress"))return video||pdf;if(action.equals("denoise"))return audio;if(action.equals("pages")||action.equals("pdf_rotate"))return pdf;if(action.equals("edit"))return image;
  if(action.equals("convert")){if(file.ext.equals("srt"))return format.equals("txt");if(image)return Tools.IMAGE_OUT.contains(format);if(pdf&&(format.equals("png")||format.equals("jpg")))return true;if(!media)return Arrays.asList("pdf","txt","docx","odt","rtf","epub","md","html").contains(format);boolean sound=Arrays.asList("mp3","wav","flac","ogg","opus","m4a","aac","aiff","wma").contains(format);return sound?audio:video&&Arrays.asList("mp4","mkv","webm","mov","avi","mpeg","ts","gif").contains(format);}
  if(!media)return (pdf&&Arrays.asList("split","merge").contains(action))||(image&&action.equals("merge"));if(Arrays.asList("trim","remove","split","merge","speed").contains(action))return true;if(Arrays.asList("mute_range","volume","fade_in","fade_out").contains(action))return audio;if(Arrays.asList("mute","add","frame","gif","rotate","subtitle").contains(action))return video;
  return video&&audio&&Arrays.asList("extract","replace").contains(action);}

 private MediaEngine engine(File work){return new MediaEngine(new MediaEngine.Host(){public void run(List<String>a)throws Exception{execute(a);}public void check()throws Exception{MainActivity.this.check();}},work);}
 private MediaEngine lightEngine(File work){return new MediaEngine(new MediaEngine.Host(){public void run(List<String>a)throws Exception{runLight(a);}public void check(){}},work);}
 private Tools.Host toolsHost(){return new Tools.Host(){public void check()throws Exception{MainActivity.this.check();}};}

 /** Produces one file's outputs exactly as the Start button does (publishing excluded). */
 List<File> produce(ListedFile entry,MediaEngine.Job j,String selectedAction,String format,boolean rich,int pages,String speechLang,boolean speechSrt,String ocrLang,SpeechEngine speechEngine,File work)throws Exception{
  final File source=entry.file;final String ext=entry.ext;final MediaEngine.Info info=entry.info;
  if(selectedAction.equals("transcribe")&&info!=null&&(j.start>=info.duration||(j.end>=0&&j.end>info.duration+.06)))throw new IOException(t("Zaman aralığı dosyanın süresini aşıyor.","Navbera demê ji dirêjahiya pelê derbas dibe."));
  if(!supportsEntry(entry,selectedAction,format))throw new IOException(t("Dosya seçili işlem veya çıktı biçimi için uygun değil.","Pel ji bo kar an formata hilbijartî ne guncav e."));List<File>outputs;
  boolean pdf=ext.equals("pdf"),image=ext.equals("image");
  if(image&&selectedAction.equals("convert")){Map<String,String> o=new HashMap<String,String>(j.opts);outputs=Arrays.asList(Tools.convertImage(source,format,o,work));}
  else if(image&&selectedAction.equals("edit")){outputs=Arrays.asList(Tools.convertImage(source,Tools.keptImageExt(entry.name),j.opts,work));}
  else if(image&&selectedAction.equals("watermark")){File up=Tools.upright(source,work);BitmapFactory.Options b=new BitmapFactory.Options();b.inJustDecodeBounds=true;BitmapFactory.decodeFile(up.getAbsolutePath(),b);
   File clean=engine(work).cleanPicture(up,b.outWidth,b.outHeight,j.opt("regions",""),j.opt("mode","fill"),"png");String keep=Tools.keptImageExt(entry.name);
   if(keep.equals("png"))outputs=Arrays.asList(clean);else{Bitmap bm=BitmapFactory.decodeFile(clean.getAbsolutePath());try{outputs=Arrays.asList(Tools.save(bm,keep,95,new File(work,"clean-final."+keep)));}finally{bm.recycle();}}}
  else if(image&&selectedAction.equals("merge")){if(other==null||!otherExt.equals("image"))throw new IOException(t("İkinci bir fotoğraf seç.","Wêneyekî din hilbijêre."));outputs=Arrays.asList(Tools.imagesToPdf(Arrays.asList(source,other),work,toolsHost()));}
  else if(pdf&&selectedAction.equals("convert")&&(format.equals("png")||format.equals("jpg")))outputs=Tools.pdfToImages(source,format,Integer.parseInt(j.opt("dpi","150")),work,toolsHost());
  else if(pdf&&selectedAction.equals("watermark")){PdfWatermark.Options o=new PdfWatermark.Options();o.auto=j.opt("auto","1").equals("1");o.repeated=j.opt("repeated","0").equals("1");o.keyword=j.opt("keyword","");o.regions=MediaEngine.regions(j.opt("regions",""));
   PdfWatermark.Result r=PdfWatermark.clean(source,work,o,new PdfWatermark.Host(){public void check()throws Exception{MainActivity.this.check();}public int surrounding(int page,double[] region){return Tools.surrounding(source,page,region);}});
   if(r.removed==0)throw new IOException("watermark_none");outputs=Arrays.asList(r.file);}
  else if(pdf&&selectedAction.equals("compress"))outputs=Arrays.asList(Tools.pdfCompress(source,Integer.parseInt(j.opt("level","2")),work,toolsHost()));
  else if(pdf&&selectedAction.equals("pages"))outputs=Arrays.asList(Tools.pdfPages(source,j.opt("spec","1"),!j.opt("keep","1").equals("0"),work));
  else if(pdf&&selectedAction.equals("pdf_rotate"))outputs=Arrays.asList(Tools.pdfRotate(source,Integer.parseInt(j.opt("angle","90")),j.opt("spec",""),work));
  else if(selectedAction.equals("subtitle_text")||(selectedAction.equals("convert")&&ext.equals("srt"))){outputs=Arrays.asList(SubtitleFiles.write(SubtitleFiles.exportText(source),"txt",work));}
  else if(selectedAction.equals("subtitle_restore")){outputs=Arrays.asList(SubtitleFiles.write(SubtitleFiles.restore(source,other),"srt",work));}
  else if(selectedAction.equals("transcribe")){String content=speechEngine.read(source,speechLang,j.start,j.end,work,speechSrt);if(content.trim().length()==0)throw new IOException(t("Konuşma algılanamadı.","Axaftin nehat dîtin."));File speechFile=new File(work,speechSrt?"speech.srt":"speech.txt");Writer writer=new OutputStreamWriter(new FileOutputStream(speechFile),"UTF-8");try{writer.write(content);}finally{writer.close();}outputs=Arrays.asList(speechFile);}
  else if(selectedAction.equals("ocr")){ocr=new OcrEngine(MainActivity.this,new OcrEngine.Host(){public void check()throws Exception{MainActivity.this.check();}public void progress(int current,int total){message(t("Sayfa okunuyor: ","Rûpel tê xwendin: ")+current+" / "+total);}});String content=ocr.read(source,ext,ocrLang);if(content.trim().length()==0)throw new IOException(t("Okunabilir yazı bulunamadı.","Nivîsa ku were xwendin nehat dîtin."));outputs=Arrays.asList(DocumentEngine.write(content,format,work));ocr=null;}
  else if(info!=null)outputs=engine(work).execute(j);
  else if(selectedAction.equals("convert")&&rich&&Arrays.asList("pdf","docx","odt","epub","html").contains(format)){RichDocument.Host host=new RichDocument.Host(){public void check()throws Exception{MainActivity.this.check();}};if(ext.equals(format)){File dest=new File(work,"document."+format);InputStream in=new FileInputStream(source);OutputStream out=new FileOutputStream(dest);try{byte[]b=new byte[65536];int n;while((n=in.read(b))!=-1){check();out.write(b,0,n);}}finally{in.close();out.close();}outputs=Arrays.asList(dest);}else outputs=Arrays.asList(RichDocument.read(source,ext,host).write(format,work,host));}
  else if(selectedAction.equals("convert")){String content=documentText(source,ext);
   if(content.trim().length()==0)throw new IOException(t("Belgede çıkarılabilir metin yok. Taranmış belgeler OCR gerektirir.","Di belgeyê de nivîsa ku derkeve tune ye. Belgeyên skankirî OCR dixwazin."));check();outputs=Arrays.asList(DocumentEngine.write(content,format,work));}
  else{if(!pdf||(selectedAction.equals("merge")&&!otherExt.equals("pdf")))throw new IOException(t("Sayfa işlemleri için PDF seç.","Ji bo karên rûpelan PDF hilbijêre."));outputs=DocumentEngine.pages(source,other,selectedAction,pages,work);}
  return outputs;}

 /** Settings of the current screen as a job; also used by the preview. */
 private MediaEngine.Job template()throws Exception{
  MediaEngine.Job j=new MediaEngine.Job();j.source=source;j.other=other;j.info=info;j.otherInfo=otherInfo;j.action=action;
  String fmt=action.equals("ocr")?val("format","PDF"):targetFormat;j.format=action.equals("subtitle")?val("subMode","burn"):fmt.toLowerCase(Locale.ROOT);
  j.start=time(val("start","0"),0);j.end=action.equals("frame")?-1:time(val("end",""),-1);j.part=time(val("part","60"),60);j.audioStart=time(val("audioStart","0"),0);j.audioEnd=time(val("audioEnd",""),-1);
  String factor=val("factor",action.equals("rotate")?"90":action.equals("speed")?"1.5":action.equals("volume")?"1.5":"1");j.factor=Double.parseDouble(factor.replace(',','.'));
  j.quality=qualityChoice==1?"high":qualityChoice==2?"small":"balanced";
  for(String k:new String[]{"mode","level","hiss","clicks","hum","voice","loud","height","keyword","auto","repeated","spec","keep","angle","flip","dpi","q","scale","gray"}){String v=vals.get(action+"."+k);if(v!=null)j.opts.put(k,v);}
  if(action.equals("watermark"))j.opts.put("regions",MediaEngine.regionText(regions));
  if(action.equals("watermark")&&!ext.equals("pdf")&&regions.isEmpty())throw new IOException(t("Önce önizlemede filigranın olduğu alanı çerçevele.","Pêşî di pêşdîtinê de qada nîşana avê çarçove bike."));
  if(Arrays.asList("merge","add","replace","subtitle_restore","subtitle").contains(action)&&other==null&&!(action.equals("merge")&&batchEnabled&&files.size()>1))throw new IOException(t("İkinci dosyayı seç.","Dosyeya duyem hilbijêre."));
  return j;}
 private static double time(String text,double fallback)throws Exception{return text==null||text.trim().length()==0?fallback:MediaEngine.seconds(text);}
 private String format(){return (action.equals("ocr")?val("format","PDF"):targetFormat.length()==0?"pdf":targetFormat).toLowerCase(Locale.ROOT);}

 private void startJob(){if(source==null){message(t("Önce dosya seç.","Berê dosyeyek hilbijêre."));return;}if(busy)return;
  if(outputTree==null){pendingStart=true;toast(t("Sonuçların kaydedileceği klasörü seç.","Peldanka ku encam lê werin tomarkirin hilbijêre."));pickOutput();return;}
  if(!ready&&info!=null){message(t("Yerel motor hazırlanıyor.","Motora herêmî tê amadekirin."));return;}
  final MediaEngine.Job template;final String selectedAction=action;final String format=format();final boolean rich=val("content","0").equals("1");final boolean speechSrt=val("speechOut","TXT").equals("SRT");final String speechLang=val("speechLang","tr");final String ocrLang=val("lang","tur+eng");final int pages;
  try{template=template();pages=info==null&&action.equals("split")?Integer.parseInt(val("pdfPart","1").trim()):1;}catch(Exception e){failure(e);return;}
  final List<ListedFile> selectedFiles=batchEnabled&&files.size()>1?new ArrayList<ListedFile>(files):Arrays.asList(files.isEmpty()||selectedIndex<0?new ListedFile(source,display,ext,info):files.get(selectedIndex));
  stopMedia();busy=true;cancelled=false;lastSummary=null;lastOutputs.clear();lastMimes.clear();batchCount=selectedFiles.size();batchIndex=0;progressTotal=0;getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);message(t("İşlem başladı…","Kar dest pê kir…"));build();
  scroller.post(new Runnable(){public void run(){if(status!=null)scroller.smoothScrollTo(0,Math.max(0,((View)status.getParent()).getTop()-dp(80)));}});
  new Thread(new Runnable(){public void run(){int saved=0,failed=0;SpeechEngine speechEngine=new SpeechEngine(MainActivity.this,new SpeechEngine.Host(){public void check()throws Exception{MainActivity.this.check();}public void run(List<String>args)throws Exception{execute(args);}public void progress(double current,double total){message(t("Konuşma yazılıyor: ","Axaftin tê nivîsandin: ")+(int)current+" / "+(int)total+t(" saniye"," çirke"));}},true);
   try{
    if(selectedAction.equals("merge")&&selectedFiles.size()>1){File work=new File(getCacheDir(),"merge-task-"+System.nanoTime());work.mkdirs();List<Uri>published=new ArrayList<Uri>();
     try{List<File>paths=new ArrayList<File>();List<MediaEngine.Info>infos=new ArrayList<MediaEngine.Info>();boolean pictures=template.info==null&&ext.equals("image");
      for(ListedFile entry:selectedFiles){check();if((pictures&&entry.ext.equals("image"))||(!pictures&&template.info==null&&entry.info==null&&entry.ext.equals("pdf"))||(template.info!=null&&entry.info!=null&&entry.info.video==template.info.video)){paths.add(entry.file);infos.add(entry.info);}else{failed++;log.append(entry.name).append(" — ").append(t("Bu işlem için uygun değil.","Ji bo vî karî ne guncav e.")).append('\n');}}
      message(t("Birleştiriliyor: ","Tê yekkirin: ")+paths.size()+t(" dosya"," dosye"));List<File>outputs;
      if(pictures)outputs=Arrays.asList(Tools.imagesToPdf(paths,work,toolsHost()));else if(template.info==null)outputs=Arrays.asList(DocumentEngine.mergeMany(paths,work,new RichDocument.Host(){public void check()throws Exception{MainActivity.this.check();}}));else outputs=engine(work).mergeMany(paths,infos);
      publishingThumb=selectedFiles.get(0).thumb;saved+=publish(outputs,display,selectedAction,published);}
     catch(Exception error){for(Uri uri:published)try{DocumentsContract.deleteDocument(getContentResolver(),uri);}catch(Exception ignored){}throw error;}finally{delete(work);}}
    else for(int index=0;index<selectedFiles.size();index++){ListedFile entry=selectedFiles.get(index);check();batchIndex=index;final String display=entry.name;final MediaEngine.Job j=MediaEngine.copy(template);j.source=entry.file;j.info=entry.info;
     progressTotal=entry.info==null?0:Arrays.asList("convert","watermark","denoise","compress","mute","volume","fade_in","fade_out","mute_range").contains(selectedAction)?entry.info.duration:0;
     message((selectedFiles.size()>1?(index+1)+"/"+selectedFiles.size()+" · ":"")+display);File work=new File(getCacheDir(),"task-"+System.nanoTime());work.mkdirs();List<Uri>published=new ArrayList<Uri>();
     try{List<File>outputs=produce(entry,j,selectedAction,format,rich,pages,speechLang,speechSrt,ocrLang,speechEngine,work);publishingThumb=entry.thumb;saved+=publish(outputs,display,selectedAction,published);}
     catch(Exception error){for(Uri uri:published)try{DocumentsContract.deleteDocument(getContentResolver(),uri);}catch(Exception ignored){}if(cancelled)throw error;failed++;log.append(display).append(" — ");failure(error);}
     finally{ocr=null;delete(work);}}
    final int count=saved,errors=failed;runOnUiThread(new Runnable(){public void run(){lastSummary=t("Kaydedilen: ","Tomarkirî: ")+count+(errors>0?t(" · Atlanan / hatalı: "," · Derbaskirî / çewt: ")+errors:"");lastStatus=count>0?t("İşlem bitti.","Kar qediya."):lastStatus;}});
   }catch(Exception error){if(cancelled)message(t("İşlem durduruldu. Tamamlanan çıktılar ve orijinaller korunuyor.","Kar hat rawestandin. Encamên qediyayî û pelên resen tên parastin."));else failure(error);}
   finally{speechEngine.close();ocr=null;publishingThumb=null;finishBusy();}}}).start();
 }
 private int publish(List<File>outputs,String display,String selectedAction,List<Uri>published)throws Exception{check();Uri parent=DocumentsContract.buildDocumentUriUsingTree(outputTree,DocumentsContract.getTreeDocumentId(outputTree));int count=0;
  for(File file:outputs){check();String suffix=file.getName().substring(file.getName().lastIndexOf('.')+1);String name=new File(display).getName().replaceFirst("\\.[^.]+$","")+"-"+slug(selectedAction)+(outputs.size()>1?"-"+(++count):"")+"."+suffix;
   String type=mime(suffix);Uri uri=DocumentsContract.createDocument(getContentResolver(),parent,type,uniqueName(parent,name));if(uri==null)throw new IOException("Cannot create output");published.add(uri);
   OutputStream dst=getContentResolver().openOutputStream(uri);InputStream src=new FileInputStream(file);try{byte[]buffer=new byte[65536];int n;while((n=src.read(buffer))!=-1){check();dst.write(buffer,0,n);}}finally{src.close();dst.close();}
   final Uri u=uri;final String m=type;final String shown=name;remember(shown,u,m,selectedAction);runOnUiThread(new Runnable(){public void run(){lastOutputs.add(u);lastMimes.add(m);}});}
  return outputs.size();}
 static String slug(String a){switch(a){case "convert":return "donusturuldu";case "watermark":return "filigransiz";case "denoise":return "temiz";case "compress":return "kucuk";case "pages":return "sayfalar";case "pdf_rotate":return "donduruldu";case "edit":return "duzenlendi";default:return a;}}

 // ---- preview
 private void runPreview(){if(busy||source==null)return;if(!ready&&info!=null){message(t("Yerel motor hazırlanıyor.","Motora herêmî tê amadekirin."));return;}
  final MediaEngine.Job j;final String act=action,fmt=format();try{j=template();}catch(Exception e){failure(e);return;}
  stopMedia();busy=true;cancelled=false;progressTotal=0;batchCount=1;batchIndex=0;preview=null;message(t("Önizleme hazırlanıyor…","Pêşdîtin tê amadekirin…"));build();
  new Thread(new Runnable(){public void run(){File work=new File(getCacheDir(),"preview");delete(work);work.mkdirs();final Preview p=new Preview();p.action=act;
   try{makePreview(p,j,act,fmt,work);runOnUiThread(new Runnable(){public void run(){preview=p;lastStatus=t("Önizleme hazır. Beğendiysen Başlat'a dokun.","Pêşdîtin amade ye. Ger baş be, Dest pê bike bitikîne.");}});}
   catch(Exception e){if(cancelled)message(t("Önizleme durduruldu.","Pêşdîtin hat rawestandin."));else failure(e);}
   finally{finishBusy();runOnUiThread(new Runnable(){public void run(){scroller.post(new Runnable(){public void run(){View o=page.findViewWithTag("preview");if(o!=null)scroller.smoothScrollTo(0,Math.max(0,o.getTop()-dp(10)));}});}});}}}).start();}
 private void makePreview(Preview p,MediaEngine.Job j,String act,String fmt,File work)throws Exception{
  ListedFile entry=new ListedFile(source,display,ext,info);
  if(info!=null){MediaEngine me=engine(work);double dur=info.duration;
   if(act.equals("frame")){File f=me.still(source,j.start,1280,"frame");p.kind="image";p.after=BitmapFactory.decodeFile(f.getAbsolutePath());return;}
   if(act.equals("remove")||act.equals("split")){double end=j.end<0?dur:Math.min(dur,j.end);List<Double> at=new ArrayList<Double>();
    if(act.equals("remove")){at.add(Math.max(0,j.start-1));at.add(Math.min(dur-0.05,end+0.05));p.captions.add(t("Silinen bölümden önce · ","Berî beşa jêbirî · ")+clock(j.start));p.captions.add(t("Sonra devam · ","Paşê berdewam · ")+clock(end));p.note=t("Yeni süre ≈ ","Dirêjahiya nû ≈ ")+clock(dur-(end-j.start));}
    else{int n=(int)Math.ceil((end-j.start)/Math.max(0.05,j.part)-1e-9);p.note=n+t(" parça oluşacak."," parçe dê çêbin.");for(int i=0;i<Math.min(n,8);i++){double s=j.start+i*j.part;at.add(s);p.captions.add((i+1)+". "+clock(s)+"–"+clock(Math.min(end,s+j.part)));}}
    if(info.video){for(int i=0;i<at.size();i++){check();File f=me.still(source,at.get(i),480,"t"+i);p.thumbs.add(BitmapFactory.decodeFile(f.getAbsolutePath()));}p.kind="thumbs";}else{p.kind="text";StringBuilder b=new StringBuilder();for(String c:p.captions)b.append(c).append('\n');p.text=b.toString().trim();}
    return;}
   if(act.equals("merge")){p.kind="text";p.text=display+" · "+clock(dur)+"\n+ "+otherDisplay+(otherInfo!=null?" · "+clock(otherInfo.duration):"");p.note=t("Toplam süre ≈ ","Dirêjahiya giştî ≈ ")+clock(dur+(otherInfo==null?0:otherInfo.duration));
    if(info.video&&otherInfo!=null&&otherInfo.video){p.kind="thumbs";p.thumbs.add(BitmapFactory.decodeFile(me.still(source,Math.min(1,dur*0.1),480,"a").getAbsolutePath()));p.captions.add("1 · "+clock(dur));p.thumbs.add(BitmapFactory.decodeFile(me.still(other,Math.min(1,otherInfo.duration*0.1),480,"b").getAbsolutePath()));p.captions.add("2 · "+clock(otherInfo.duration));}
    return;}
   // Everything else: run the real operation on a short piece.
   double len=act.equals("denoise")?10:act.equals("trim")?Math.min(8,(j.end<0?dur:j.end)-j.start):6;
   double from=act.equals("denoise")?time(val("at","0"),0):Arrays.asList("convert","compress","watermark","mute","subtitle").contains(act)?Math.min(Math.max(0,dur*0.1),Math.max(0,dur-len)):j.start;
   if(act.equals("speed"))len=Math.min(8,Math.max(2,(j.end<0?dur:j.end)-j.start));
   message(t("Örnek parça hazırlanıyor…","Mînak tê amadekirin…"));File sample=me.sample(source,info,from,len,"sample");MediaEngine.Info si=probe(sample);
   if(act.equals("trim")){p.kind=info.video?"video":"audio";p.result=sample;if(!info.video)p.peaksB=wavePeaks(sample,90);p.note=t("Kesilecek bölümün ilk ","Destpêka beşa ku tê birîn: ")+clock(len)+t("’i."," .");return;}
   MediaEngine.Job k=MediaEngine.copy(j);k.source=sample;k.info=si;
   if(Arrays.asList("convert","compress","watermark","mute","subtitle","denoise").contains(act)){k.start=0;k.end=-1;}
   else{k.start=Math.max(0,j.start-from);k.end=j.end<0?-1:Math.min(si.duration,j.end-from);if(k.end>=0&&k.end<=k.start+0.05){k.start=0;k.end=-1;}}
   if(act.equals("subtitle")){p.note=t("Örnek, videonun ","Mînak ji ")+clock(from)+t(" anından başlar; altyazı o anda yoksa görünmez."," dest pê dike; ger binnivîs tune be xuya nabe.");File shifted=shiftSubtitle(other,from,work);if(shifted!=null)k.other=shifted;}
   message(t("Önizleme işleniyor…","Pêşdîtin tê kirin…"));List<File> out=engine(new File(work,"run")).execute(k);File r=out.get(0);p.result=r;p.original=sample;
   if(act.equals("convert")||act.equals("compress")){long est=(long)(r.length()/Math.max(0.5,si.duration)*dur);p.note=t("Tahmini çıktı boyutu ≈ ","Mezinahiya texmînî ≈ ")+size(est)+t(" (şu an "," (niha ")+size(source.length())+")";}
   if(r.getName().endsWith(".gif")){p.kind="gif";return;}
   if(r.getName().endsWith(".png")){p.kind="image";p.after=BitmapFactory.decodeFile(r.getAbsolutePath());return;}
   if(act.equals("denoise")||!info.video||isAudio(r)){File a=listenable(sample,work,"a"),b=listenable(r,work,"b");p.original=a;p.result=b;p.peaksA=wavePeaks(a,90);p.peaksB=wavePeaks(b,90);p.kind="audio";
    if(act.equals("denoise"))p.note=t("10 saniyelik örnek: Orijinal ile Sonuç arasında geçiş yaparak dinle.","Mînaka 10 çirkeyan: di navbera Resen û Encamê de biguherîne û guhdarî bike.");return;}
   if(act.equals("watermark")){double mid=Math.min(1,si.duration/2);p.before=BitmapFactory.decodeFile(me.still(sample,mid,1280,"wa").getAbsolutePath());p.after=BitmapFactory.decodeFile(engine(work).still(r,mid,1280,"wb").getAbsolutePath());p.kind="compare";return;}
   if(!r.getName().endsWith(".mp4")&&!r.getName().endsWith(".webm")&&!r.getName().endsWith(".mkv")){File mp4=new File(work,"play.mp4");List<String> a=new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",r.getAbsolutePath(),"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-y",mp4.getAbsolutePath()));execute(a);p.result=mp4;}
   p.kind="video";return;}
  if(ext.equals("pdf")){
   if(act.equals("ocr")){Bitmap b=Tools.renderPage(source,pdfPage,1800);File png=new File(work,"page.png");Tools.save(b,"png",100,png);b.recycle();ocr=new OcrEngine(this,new OcrEngine.Host(){public void check()throws Exception{MainActivity.this.check();}public void progress(int c,int t){}});try{p.text=ocr.read(png,"image",val("lang","tur+eng")).trim();}finally{ocr=null;}p.kind="text";p.note=t("Yalnızca bu sayfa okundu.","Tenê ev rûpel hat xwendin.");if(p.text.length()==0)p.text="—";return;}
   if(act.equals("convert")&&!fmt.equals("png")&&!fmt.equals("jpg")){String s=documentText(source,"pdf");p.kind="text";p.text=s.length()>1500?s.substring(0,1500)+"…":s;p.note=t("Çıktıya aktarılacak metnin başı.","Destpêka nivîsa ku dê derbas bibe.");return;}
   MediaEngine.Job k=MediaEngine.copy(j);List<File> out=produce(entry,k,act,fmt,false,act.equals("split")?Integer.parseInt(val("pdfPart","1").trim()):1,"tr",false,"tur+eng",null,work);File first=out.get(0);
   if(act.equals("watermark")||act.equals("compress")){int pg=Math.min(pdfPage,Tools.pageCount(first)-1);p.before=Tools.renderPage(source,pdfPage,1100);p.after=Tools.renderPage(first,pg,1100);p.kind="compare";
    p.note=act.equals("compress")?t("Yeni boyut: ","Mezinahiya nû: ")+size(first.length())+t(" (önce "," (berê ")+size(source.length())+")":t("Bu sayfada önce/sonra. Diğer sayfalara yukarıdaki oklarla geçip yeniden önizleyebilirsin.","Berê/paşê li vê rûpelê. Bi tîrên jorîn here rûpelên din û dîsa pêşdîtin bike.");return;}
   if(fmt.equals("png")||fmt.equals("jpg")){p.kind="thumbs";for(int i=0;i<Math.min(8,out.size());i++){Bitmap b=Tools.load(out.get(i),700);p.thumbs.add(b);p.captions.add(t("Sayfa ","Rûpel ")+(i+1));}p.note=out.size()+t(" resim oluşacak."," wêne dê çêbibin.");return;}
   p.kind="thumbs";if(act.equals("split")){for(int i=0;i<Math.min(8,out.size());i++){p.thumbs.add(Tools.renderPage(out.get(i),0,360));p.captions.add((i+1)+". "+t("dosya · ","dosye · ")+Tools.pageCount(out.get(i))+t(" sayfa"," rûpel"));}p.note=out.size()+t(" PDF oluşacak."," PDF dê çêbin.");}
   else{int n=Tools.pageCount(first);for(int i=0;i<Math.min(10,n);i++){p.thumbs.add(Tools.renderPage(first,i,360));p.captions.add(t("Sayfa ","Rûpel ")+(i+1));}p.note=t("Sonuç: ","Encam: ")+n+t(" sayfa"," rûpel");}
   return;}
  if(ext.equals("image")){
   if(act.equals("ocr")){ocr=new OcrEngine(this,new OcrEngine.Host(){public void check()throws Exception{MainActivity.this.check();}public void progress(int c,int t){}});try{p.text=ocr.read(source,"image",val("lang","tur+eng")).trim();}finally{ocr=null;}if(p.text.length()==0)p.text="—";p.kind="text";return;}
   List<File> out=produce(entry,MediaEngine.copy(j),act,fmt,false,1,"tr",false,"tur+eng",null,work);File r=out.get(0);
   if(r.getName().endsWith(".pdf")){p.kind="thumbs";int n=Tools.pageCount(r);for(int i=0;i<Math.min(8,n);i++){p.thumbs.add(Tools.renderPage(r,i,360));p.captions.add(t("Sayfa ","Rûpel ")+(i+1));}p.note=t("Boyut: ","Mezinahî: ")+size(r.length());return;}
   Bitmap after=Tools.load(r,1600);p.note=t("Boyut: ","Mezinahî: ")+size(r.length())+t(" (önce "," (berê ")+size(source.length())+") · "+after.getWidth()+"×"+after.getHeight();
   if(act.equals("watermark")||(base!=null&&Math.abs((float)after.getWidth()/after.getHeight()-(float)base.getWidth()/base.getHeight())<0.02f)){p.before=base!=null?base:Tools.load(source,1600);p.after=after;p.kind="compare";}else{p.after=after;p.kind="image";}
   return;}
  // Other documents: the text that will be converted.
  String s=ext.equals("srt")||ext.equals("txt")?readFile(source):documentText(source,ext);p.kind="text";p.text=s.length()>1500?s.substring(0,1500)+"…":s;}
 /** A subtitle moved earlier so that a preview piece starting later shows the right lines. */
 private File shiftSubtitle(File sub,double by,File work){try{if(sub==null||!sub.getName().toLowerCase(Locale.ROOT).endsWith(".srt"))return null;File out=new File(work,"shifted.srt");List<String> a=new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-itsoffset",MediaEngine.n(-by),"-i",sub.getAbsolutePath(),"-y",out.getAbsolutePath()));runLight(a);return out.isFile()?out:null;}catch(Exception e){return null;}}
 /** Something MediaPlayer can always play: WAV for unusual sound formats and for video. */
 private File listenable(File f,File work,String name)throws Exception{String n=f.getName().toLowerCase(Locale.ROOT);if(n.endsWith(".mp3")||n.endsWith(".wav")||n.endsWith(".m4a")||n.endsWith(".ogg")||n.endsWith(".flac"))return f;File out=new File(work,name+".wav");execute(new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",f.getAbsolutePath(),"-vn","-ac","2","-ar","44100","-y",out.getAbsolutePath())));return out;}
 /** Loudness of the sound in `bars` slices, 0–1. */
 private float[] wavePeaks(File f,int bars){try{File raw=new File(getCacheDir(),"wave-"+System.nanoTime()+".raw");try{runLight(new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-i",f.getAbsolutePath(),"-vn","-ac","1","-ar","2000","-f","s16le","-progress","pipe:1","-y",raw.getAbsolutePath())));
   long samples=raw.length()/2;if(samples<bars)return new float[0];float[] out=new float[bars];DataInputStream in=new DataInputStream(new BufferedInputStream(new FileInputStream(raw)));float max=1;
   try{for(int b=0;b<bars;b++){long from=samples*b/bars,to=samples*(b+1)/bars;double sum=0;for(long i=from;i<to;i++){int lo=in.read(),hi=in.read();short v=(short)((hi<<8)|lo);sum+=(double)v*v;}out[b]=(float)Math.sqrt(sum/Math.max(1,to-from));max=Math.max(max,out[b]);}}finally{in.close();}
   for(int b=0;b<bars;b++)out[b]=(float)Math.pow(out[b]/max,0.7);return out;}finally{raw.delete();}}catch(Exception e){return new float[0];}}

 // =====================================================================================
 // Files, native engine and processes
 // =====================================================================================
 private void choose(int request){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("*/*");if(request==1)i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);i.addCategory(Intent.CATEGORY_OPENABLE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(i,request);}
 private ListedFile importFile(Uri uri)throws Exception{
  check();String name="dosya";Cursor c=getContentResolver().query(uri,null,null,null,null);if(c!=null)try{if(c.moveToFirst()){int col=c.getColumnIndex(OpenableColumns.DISPLAY_NAME);if(col>=0)name=c.getString(col);}}finally{c.close();}
  String suffix=name.contains(".")?name.substring(name.lastIndexOf('.')+1).toLowerCase(Locale.ROOT):"bin";File file=File.createTempFile("selected-","."+suffix,getCacheDir());boolean success=false;try{InputStream input=getContentResolver().openInputStream(uri);try{OutputStream out=new FileOutputStream(file);try{byte[]buffer=new byte[65536];int n;while((n=input.read(buffer))!=-1){check();out.write(buffer,0,n);}}finally{out.close();}}finally{input.close();}
  ListedFile entry=classify(file,name,suffix);success=true;return entry;}finally{if(!success)file.delete();}
 }
 /** Second file (merge partner, audio to add, subtitle, original SRT) as the picker would set it. */
 void useOther(ListedFile f){other=f==null?null:f.file;otherExt=f==null?"":f.ext;otherInfo=f==null?null:f.info;otherDisplay=f==null?"":f.name;}
 /** File type detection shared by the file picker and the full self test. */
 ListedFile classify(File file,String name,String suffix)throws Exception{
  suffix=detectDocument(file,suffix);MediaEngine.Info found=null;if(!Arrays.asList("srt","pdf","txt","md","rtf","html","htm","docx","odt","odp","pptx","xlsx","epub","csv","tsv","rst","image").contains(suffix)){if(!ready)throw new IOException(t("Yerel motor henüz hazır değil.","Motora herêmî hîn ne amade ye."));found=probe(file);}return new ListedFile(file,name,suffix,found);
 }
 private List<Uri> treeFiles(Uri tree)throws Exception{return treeFilesFrom(tree,DocumentsContract.getTreeDocumentId(tree));}
 private List<Uri> treeFilesFrom(Uri tree,String rootId)throws Exception{List<Uri> result=new ArrayList<Uri>();ArrayDeque<String>queue=new ArrayDeque<String>();Set<String>seen=new HashSet<String>();queue.add(rootId);while(!queue.isEmpty()){check();String id=queue.removeFirst();if(!seen.add(id))continue;Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,id);Cursor c=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,DocumentsContract.Document.COLUMN_DISPLAY_NAME);if(c!=null)try{while(c.moveToNext()){check();String child=c.getString(0);if(DocumentsContract.Document.MIME_TYPE_DIR.equals(c.getString(1)))queue.add(child);else result.add(DocumentsContract.buildDocumentUriUsingTree(tree,child));}}finally{c.close();}}return result;}
 private void importMany(final List<Uri>input,final Uri tree){if(busy){openImported=false;toast(t("Önce süren işlemi bitir.","Pêşî karê heyî biqedîne."));return;}busy=true;cancelled=false;message(t("Dosyalar ekleniyor…","Dosye tên zêdekirin…"));build();
  new Thread(new Runnable(){public void run(){final List<ListedFile>found=new ArrayList<ListedFile>();int failures=0;
   try{for(int i=0;i<600&&!ready;i++)Thread.sleep(200);List<Uri>uris=tree==null?input:treeFiles(tree);int n=0;
    for(Uri uri:uris){check();n++;message(t("Ekleniyor: ","Tê zêdekirin: ")+n+" / "+uris.size());try{ListedFile f=importFile(uri);f.thumb=makeThumb(f);found.add(f);}catch(Exception error){if(cancelled)throw error;failures++;failure(error);}}}
   catch(Exception error){if(!cancelled)failure(error);}
   final int skipped=failures;runOnUiThread(new Runnable(){public void run(){files.addAll(found);if(files.size()>1)batchEnabled=false;busy=false;
    lastStatus=t("Listeye eklendi: ","Li lîsteyê zêde bûn: ")+found.size()+(skipped>0?t(" · Atlanan / hatalı: "," · Derbaskirî / çewt: ")+skipped:"");homeNotice=skipped>0?lastStatus+"\n"+log.toString().trim():null;
    boolean open=openImported;openImported=false;if(found.size()==1&&(open||files.size()==1)){selectFile(files.size()-1);applyQuick();}else{quickAction=null;go("home");}}});}}).start();}
 /** Small picture for the file list and the history. */
 private File makeThumb(ListedFile f){try{File dir=new File(getCacheDir(),"thumbs");dir.mkdirs();File out=new File(dir,"t-"+System.nanoTime()+".jpg");Bitmap b=null;
   if(f.info!=null&&f.info.video){File s=lightEngine(dir).still(f.file,Math.min(1,f.info.duration*0.1),240,"s-"+System.nanoTime());b=BitmapFactory.decodeFile(s.getAbsolutePath());s.delete();}
   else if(f.ext.equals("image"))b=Tools.load(f.file,240);else if(f.ext.equals("pdf"))b=Tools.renderPage(f.file,0,200);
   if(b==null)return null;Tools.save(b,"jpg",80,out);b.recycle();return out;}catch(Exception e){return null;}}
 protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null){pendingStart=false;return;}final Uri uri=data.getData();
  if(request==4&&uri!=null){importMany(null,uri);return;}
  if(request==1&&data.getClipData()!=null){List<Uri>uris=new ArrayList<Uri>();for(int i=0;i<data.getClipData().getItemCount();i++)uris.add(data.getClipData().getItemAt(i).getUri());importMany(uris,null);return;}
  if(uri==null)return;
  if(request==3){try{getContentResolver().takePersistableUriPermission(uri,data.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION));outputTree=uri;getPreferences(0).edit().putString("tree",uri.toString()).apply();build();if(pendingStart){pendingStart=false;startJob();}}catch(Exception error){failure(error);}return;}
  if(request==1){importMany(Arrays.asList(uri),null);return;}
  busy=true;cancelled=false;build();new Thread(new Runnable(){public void run(){try{final ListedFile entry=importFile(uri);runOnUiThread(new Runnable(){public void run(){useOther(entry);preview=null;busy=false;build();}});}catch(Exception error){failure(error);finishBusy();}}}).start();}
 String detectDocument(File f,String fallback)throws Exception {
  FileInputStream in=new FileInputStream(f);byte[]head=new byte[4096];int n;try{n=in.read(head);}finally{in.close();}
  if(n>=5&&new String(head,0,5,"US-ASCII").equals("%PDF-"))return "pdf";
  if(n>=6&&(new String(head,0,6,"US-ASCII").equals("GIF87a")||new String(head,0,6,"US-ASCII").equals("GIF89a")))return "gif";
  android.graphics.BitmapFactory.Options imageBounds=new android.graphics.BitmapFactory.Options();imageBounds.inJustDecodeBounds=true;android.graphics.BitmapFactory.decodeFile(f.getAbsolutePath(),imageBounds);if(imageBounds.outWidth>0&&imageBounds.outHeight>0)return "image";
  if(n>=2&&head[0]=='P'&&head[1]=='K'){
   ZipFile zip=new ZipFile(f);try{
    if(zip.getEntry("word/document.xml")!=null)return "docx";
    if(zip.getEntry("ppt/presentation.xml")!=null)return "pptx";
    if(zip.getEntry("xl/workbook.xml")!=null)return "xlsx";
    if(zip.getEntry("content.xml")!=null){
     ZipEntry mime=zip.getEntry("mimetype");String type="";
     if(mime!=null){InputStream m=zip.getInputStream(mime);try{byte[] b=new byte[256];int count=m.read(b);if(count>0)type=new String(b,0,count,"US-ASCII").trim();}finally{m.close();}}
     if(type.equals("application/vnd.oasis.opendocument.presentation"))return "odp";
     if(type.equals("application/vnd.oasis.opendocument.spreadsheet"))throw new IOException(t("ODS elektronik tabloları henüz desteklenmiyor.","Tabloyên ODS hîn nayên piştgirîkirin."));
     return "odt";
    }
    if(zip.getEntry("META-INF/container.xml")!=null)return "epub";
   }finally{zip.close();}throw new IOException(t("Bu ZIP dosyası desteklenen bir belge değil.","Ev dosyeya ZIP ne belgeyeke piştgirîkirî ye."));
  }
  if(n>=2&&((head[0]==(byte)0xff&&head[1]==(byte)0xfe)||(head[0]==(byte)0xfe&&head[1]==(byte)0xff)))return "txt";
  for(int i=0;i<n;i++)if(head[i]==0)return "bin";
  String start=new String(head,0,Math.max(0,n),"UTF-8").trim();if(fallback.equals("srt")||start.matches("(?s).*\\d{2}:\\d{2}:\\d{2},\\d{3} --> .*"))return "srt";
  if(start.startsWith("{\\rtf"))return "rtf";
  if(start.toLowerCase(Locale.ROOT).contains("<html")||start.toLowerCase(Locale.ROOT).startsWith("<!doctype html"))return "html";
  if(Arrays.asList("txt","md","csv","tsv","rst","html","htm","rtf").contains(fallback))return fallback;
  try{java.nio.charset.CharsetDecoder decoder=java.nio.charset.Charset.forName("UTF-8").newDecoder();java.nio.charset.CoderResult result=decoder.decode(java.nio.ByteBuffer.wrap(head,0,Math.max(n,0)),java.nio.CharBuffer.allocate(8192),false);if(!result.isError()){int controls=0;for(int i=0;i<n;i++)if(head[i]>=0&&head[i]<32&&head[i]!='\n'&&head[i]!='\r'&&head[i]!='\t')controls++;if(controls<Math.max(1,n/20))return "txt";}}catch(Exception ignored){}
  return "bin";
 }
 /** Document text; PDF pages whose text is only drawn as pictures are read with OCR. */
 String documentText(File source,String ext)throws Exception{String content=DocumentEngine.read(source,ext);
  if(ext.equals("pdf")&&meaningful(content)<20*pdfPages(source)){
   message(t("Belgedeki yazılar resim olarak gömülü; OCR ile okunuyor…","Nivîs di belgeyê de wek wêne ye; bi OCR tê xwendin…"));
   OcrEngine engine=new OcrEngine(this,new OcrEngine.Host(){public void check()throws Exception{MainActivity.this.check();}public void progress(int current,int total){message(t("Sayfa okunuyor: ","Rûpel tê xwendin: ")+current+" / "+total);}});
   ocr=engine;try{String read=engine.read(source,"pdf","tur+eng");if(meaningful(read)>meaningful(content))content=read;}finally{ocr=null;}}
  return content;}
 static int meaningful(String text){int n=0;for(int i=0;i<text.length();i++)if(Character.isLetterOrDigit(text.charAt(i)))n++;return n;}
 static int pdfPages(File f){try{com.tom_roush.pdfbox.pdmodel.PDDocument d=com.tom_roush.pdfbox.pdmodel.PDDocument.load(f);try{return Math.max(1,d.getNumberOfPages());}finally{d.close();}}catch(Exception e){return 1;}}
 private void prepareNative()throws Exception {
  libraries=new File(getFilesDir(),"ffmpeg-runtime");File archive=new File(getApplicationInfo().nativeLibraryDir,"libffmpeg.zip.so");File marker=new File(libraries,"ready-"+archive.length());if(marker.exists())return;libraries.mkdirs();
  ZipInputStream z=new ZipInputStream(new FileInputStream(archive));String links="{}";try{ZipEntry e;byte[]b=new byte[65536];while((e=z.getNextEntry())!=null){File dest=new File(libraries,e.getName());if(!dest.getCanonicalPath().startsWith(libraries.getCanonicalPath()+File.separator))throw new IOException("Unsafe archive path");if(e.isDirectory()){dest.mkdirs();continue;}dest.getParentFile().mkdirs();FileOutputStream out=new FileOutputStream(dest);try{int n;while((n=z.read(b))!=-1)out.write(b,0,n);}finally{out.close();}}}finally{z.close();}
  File mappings=new File(libraries,"_links.json");if(mappings.exists()){JSONObject aliases=new JSONObject(readFile(mappings));Iterator<String> it=aliases.keys();while(it.hasNext()){String name=it.next();File dest=new File(libraries,name);String target=aliases.getString(name);if(!new File(dest.getParentFile(),target).getCanonicalPath().startsWith(libraries.getCanonicalPath()+File.separator))throw new IOException("Unsafe library link");if(!dest.exists())Os.symlink(target,dest.getAbsolutePath());}}
  marker.createNewFile();
 }
 private String readFile(File f)throws Exception {FileInputStream in=new FileInputStream(f);try{ByteArrayOutputStream out=new ByteArrayOutputStream();byte[]b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return new String(out.toByteArray(),"UTF-8");}finally{in.close();}}
 void check()throws Exception{if(cancelled)throw new InterruptedIOException("Cancelled");}
 String execute(List<String> args)throws Exception{return run(args,true);}
 /** Background helper processes (thumbnails, waveforms): not tied to the Stop button. */
 String runLight(List<String> args)throws Exception{return run(args,false);}
 private String run(List<String> args,final boolean primary)throws Exception{
  if(primary)check();List<String> command=new ArrayList<String>(args);String executable=command.remove(0);command.add(0,new File(getApplicationInfo().nativeLibraryDir,executable.equals("ffprobe")?"libffprobe.so":"libffmpeg.so").getAbsolutePath());
  ProcessBuilder pb=new ProcessBuilder(command);pb.redirectErrorStream(true);pb.environment().put("LD_LIBRARY_PATH",new File(libraries,"usr/lib").getAbsolutePath()+":"+getApplicationInfo().nativeLibraryDir);pb.environment().put("HOME",getFilesDir().getAbsolutePath());pb.environment().put("TMPDIR",getCacheDir().getAbsolutePath());
  final java.lang.Process started=pb.start();if(primary)process=started;final java.util.concurrent.atomic.AtomicLong lastLine=new java.util.concurrent.atomic.AtomicLong(System.currentTimeMillis());final java.util.concurrent.atomic.AtomicBoolean timedOut=new java.util.concurrent.atomic.AtomicBoolean(false);
  final Timer watchdog=new Timer(true);watchdog.schedule(new TimerTask(){public void run(){if(primary&&cancelled)force(started);else if(System.currentTimeMillis()-lastLine.get()>(primary?120000:60000)){timedOut.set(true);force(started);}}},250,250);if(primary&&cancelled)force(started);
  try{BufferedReader r=new BufferedReader(new InputStreamReader(started.getInputStream(),"UTF-8"));StringBuilder result=new StringBuilder();String line;
   while((line=r.readLine())!=null){lastLine.set(System.currentTimeMillis());if(result.length()<2*1024*1024)result.append(line).append('\n');if(primary&&cancelled)force(started);
    if(primary&&progressTotal>0&&line.startsWith("out_time_us=")){try{double done=Long.parseLong(line.substring(12).trim())/1e6;final int value=(int)Math.max(0,Math.min(1000,(batchIndex+Math.min(1,done/progressTotal))/Math.max(1,batchCount)*1000));runOnUiThread(new Runnable(){public void run(){if(progress!=null){progress.setIndeterminate(false);progress.setProgress(value);}if(percent!=null)percent.setText("%"+value/10);}});}catch(Exception ignored){}}}
   int code=started.waitFor();watchdog.cancel();if(primary)process=null;if(primary)check();if(timedOut.get())throw new IOException(t("İşlem uzun süre yanıt vermedi; durduruldu.","Kar demeke dirêj bersiv neda; hat rawestandin."));if(code!=0)throw new IOException(result.length()>3000?result.substring(result.length()-3000):result.toString());return result.toString();}
  finally{watchdog.cancel();if(primary)process=null;}
 }
 MediaEngine.Info probe(File f)throws Exception {
  // Real files often carry broken tags; ffprobe then prints warnings on stderr, which share
  // this output stream. Keep it quiet and read only the JSON object itself.
  String out=execute(new ArrayList<String>(Arrays.asList("ffprobe","-v","quiet","-protocol_whitelist","file,pipe","-show_format","-show_streams","-of","json",f.getAbsolutePath())));
  int from=out.indexOf('{'),to=out.lastIndexOf('}');if(from<0||to<from)throw new IOException(t("Dosyanın ses/video bilgisi okunamadı.","Agahiyên deng/vîdyoyê yên pelê nehatin xwendin."));
  JSONObject json=new JSONObject(out.substring(from,to+1));MediaEngine.Info i=new MediaEngine.Info();JSONArray streams=json.getJSONArray("streams");
  for(int n=0;n<streams.length();n++){JSONObject s=streams.getJSONObject(n);if(s.optString("codec_type").equals("audio"))i.audio=true;
   if(s.optString("codec_type").equals("video")&&(s.optJSONObject("disposition")==null||s.optJSONObject("disposition").optInt("attached_pic")!=1)&&!i.video){i.video=true;i.width=s.optInt("width");i.height=s.optInt("height");String[]rate=s.optString("avg_frame_rate","25/1").split("/");try{i.fps=Double.parseDouble(rate[0])/Double.parseDouble(rate[1]);if(!MediaEngine.finite(i.fps)||i.fps<=0)i.fps=25;}catch(Exception ignored){}
    int rot=0;JSONArray side=s.optJSONArray("side_data_list");if(side!=null)for(int k=0;k<side.length();k++)if(side.getJSONObject(k).has("rotation"))rot=side.getJSONObject(k).optInt("rotation");JSONObject tags=s.optJSONObject("tags");if(rot==0&&tags!=null)rot=tags.optInt("rotate",0);i.rotation=((Math.abs(rot)%360)+360)%360;}}
  i.duration=json.getJSONObject("format").optDouble("duration",0);if((!i.video&&!i.audio)||i.duration<=0)throw new IOException(t("Bu dosyanın türü veya süresi belirlenemedi.","Cure an dirêjahiya vê dosyeyê nehat naskirin."));return i;
 }
 private String uniqueName(Uri parent,String name)throws Exception {Set<String> names=new HashSet<String>();Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(outputTree,DocumentsContract.getDocumentId(parent));Cursor c=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null);if(c!=null)try{while(c.moveToNext())names.add(c.getString(0));}finally{c.close();}int dot=name.lastIndexOf('.');String stem=dot<0?name:name.substring(0,dot),suffix=dot<0?"":name.substring(dot),candidate=name;for(int n=1;names.contains(candidate);n++)candidate=stem+" ("+n+")"+suffix;return candidate;}
 private String mime(String ext){if(ext.equals("srt"))return "application/x-subrip";if(ext.equals("mp3"))return "audio/mpeg";if(ext.equals("m4a"))return "audio/mp4";if(ext.equals("mkv"))return "video/x-matroska";if(ext.equals("mov"))return "video/quicktime";if(ext.equals("avi"))return "video/x-msvideo";if(ext.equals("ts"))return "video/mp2t";if(ext.equals("wma"))return "audio/x-ms-wma";if(ext.equals("aiff"))return "audio/x-aiff";if(ext.equals("opus"))return "audio/ogg";if(ext.equals("pdf"))return "application/pdf";if(ext.equals("docx"))return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";if(ext.equals("odt"))return "application/vnd.oasis.opendocument.text";if(ext.equals("epub"))return "application/epub+zip";if(ext.equals("rtf"))return "application/rtf";if(Arrays.asList("txt","md","html").contains(ext))return ext.equals("html")?"text/html":"text/plain";if(Arrays.asList("png","gif","webp","bmp").contains(ext))return "image/"+ext;if(ext.equals("jpg")||ext.equals("jpeg"))return "image/jpeg";if(Arrays.asList("mp4","webm","mpeg").contains(ext))return "video/"+ext;if(Arrays.asList("wav","flac","ogg","aac").contains(ext))return "audio/"+ext;return "application/octet-stream";}
 private void delete(File f){if(f.isDirectory()){File[]children=f.listFiles();if(children!=null)for(File c:children)delete(c);}f.delete();}
 private void finishBusy(){runOnUiThread(new Runnable(){public void run(){busy=false;progressTotal=0;getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);build();}});}
 private static void force(java.lang.Process p){try{java.lang.Process.class.getMethod("destroyForcibly").invoke(p);}catch(Exception ignored){p.destroy();}}
 private void cancel(){cancelled=true;if(ocr!=null)ocr.cancel();java.lang.Process p=process;if(p!=null)force(p);message(t("Durduruluyor…","Tê rawestandin…"));}
 void message(final String value){lastStatus=value;runOnUiThread(new Runnable(){public void run(){if(status!=null)status.setText(value);}});}
 static String imageError(String key,boolean ku){
  if("speech_memory_low".equals(key))return ku?"Ji bo nivîsandina axaftinê amûreke bi 4 GB RAM û bi kêmî 1,5 GB RAM a vala pêwîst e. Sepanên din bigire an amûreke bi RAM a zêdetir bi kar bîne.":"Konuşmayı yazıya dökmek için 4 GB RAM bulunan bir cihaz ve en az 1,5 GB boş RAM gerekiyor. Diğer uygulamaları kapat veya daha fazla RAM bulunan bir cihaz kullan.";
  if("subtitle_invalid".equals(key))return ku?"Formata SRT an demkod ne rast in.":"SRT biçimi veya zaman kodları geçersiz.";
  if("subtitle_line_count".equals(key))return ku?"Hejmara rêzên TXT û SRT divê yek be. Rêzan vala nehêle.":"TXT satır sayısı orijinal SRT ile aynı olmalı. Satırları birleştirme, bölme veya boş bırakma.";
  if("image_reference_unavailable".equals(key))return ku?"Di belgeyê de gihîştina wêneyekê ne pêkan e. Wêneyê di belgeyê de tomar bike û dîsa biceribîne, an Tenê nivîs hilbijêre.":"Belgedeki bir görsele erişilemiyor. Görseli belgeye gömerek yeniden kaydet ya da Yalnızca metin seçeneğini kullan.";
  if("external_image_unavailable".equals(key))return ku?"Wêne ji girêdaneke derve nayê daxistin. Ji bo bikaranîna bê înternetê wêneyê di belgeyê de tomar bike, an Tenê nivîs hilbijêre.":"Dış bağlantıdaki görsel indirilmiyor. Çevrimdışı kullanım için görseli belgeye gömerek kaydet ya da Yalnızca metin seçeneğini kullan.";
  if("watermark_none".equals(key))return ku?"Nîşana avê bixweber nehat dîtin. Nivîsa nîşana avê binivîse an di pêşdîtina rûpelê de qadê çarçove bike.":"Filigran otomatik bulunamadı. Filigrandaki yazıyı gir ya da sayfa önizlemesinde alanı çerçevele.";
  if("page_range".equals(key))return ku?"Rêza rûpelan ne derbasdar e. Mînak: 1-3, 5, 8-":"Sayfa aralığı geçersiz. Örnek: 1-3, 5, 8-";
  if("Choose the watermark area".equals(key))return ku?"Pêşî di pêşdîtinê de qada nîşana avê çarçove bike.":"Önce önizlemede filigranın olduğu alanı çerçevele.";
  if("Choose what to clean".equals(key))return ku?"Herî kêm tiştekî ji bo paqijkirinê hilbijêre.":"Temizlenecek en az bir şey seç.";
  if("No audio track".equals(key))return ku?"Di vê dosyeyê de deng tune ye.":"Bu dosyada ses yok.";
  return null;
 }
 private void failure(final Exception e){String detail=imageError(e.getMessage(),ku);if(detail==null&&(e instanceof IOException||e instanceof IllegalArgumentException)&&e.getMessage()!=null&&!(e instanceof InterruptedIOException)&&e.getMessage().indexOf('\n')<0&&!e.getMessage().startsWith("/"))detail=e.getMessage();final String value=t("İşlem tamamlanamadı: ","Kar nehat temamkirin: ")+(detail==null?e.toString():detail);log.append(value).append('\n');lastStatus=value;runOnUiThread(new Runnable(){public void run(){if(status!=null)status.setText(value);else toast(value);}});}
 /** Android 16 sends Back through the dispatcher; older versions call onBackPressed. Both land here. */
 private void registerBack(){if(Build.VERSION.SDK_INT>=33)getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,new android.window.OnBackInvokedCallback(){public void onBackInvoked(){handleBack();}});}
 public void onBackPressed(){handleBack();}
 private void handleBack(){if(busy){new AlertDialog.Builder(this).setMessage(t("İşlemi durdurup çıkılsın mı?","Kar were rawestandin û derkeve?" )).setPositiveButton(t("Durdur ve çık","Rawestîne û derkeve"),new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int n){cancel();finish();}}).setNegativeButton(t("Devam et","Berdewam bike"),null).show();return;}
  if(!screen.equals("home")){go("home");return;}if(isTaskRoot())moveTaskToBack(true);else finish();}
 protected void onDestroy(){if(isFinishing())cancelled=true;stopMedia();super.onDestroy();}
}
