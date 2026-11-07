package org.local.donusturucu;
import android.animation.*;import android.app.Activity;import android.content.*;import android.database.Cursor;import android.graphics.*;import android.graphics.drawable.*;import android.media.MediaPlayer;import android.net.Uri;import android.os.*;import android.provider.OpenableColumns;import android.util.LruCache;import android.view.*;import android.view.animation.DecelerateInterpolator;import android.widget.*;
import java.io.*;import java.util.*;
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader;

/** Quick look: a tap on a file in the file manager opens a panel from the bottom over the file list, showing the
 *  picture, pages, video, sound or text at once. "Dönüştür" takes the file on to the workspace; tapping outside
 *  or pulling the panel down closes it. */
public class QuickView extends Activity {
 static final List<String> IMAGES=Arrays.asList("jpg","jpeg","jfif","png","webp","bmp","gif","heic","heif");
 static final List<String> VIDEOS=Arrays.asList("mp4","m4v","mkv","webm","mov","3gp","avi","ts","mpg","mpeg");
 static final List<String> SOUNDS=Arrays.asList("mp3","m4a","aac","wav","ogg","oga","opus","flac","amr","wma","mka");
 static final List<String> TEXTS=Arrays.asList("txt","srt","vtt","md","csv","tsv","rst","log","json","xml");
 static final List<String> DOCS=Arrays.asList("docx","odt","epub","html","htm","rtf","pptx","odp","xlsx");

 private Ui ui;private boolean ku,dark,full=false,closing=false;private Uri uri;private String mime,name="",ext="",kind="";private long size=-1;
 private View dim;private LinearLayout sheet,controls,shortcuts;private ScrollView body;private String chosen="";private TextView goButton;private FrameLayout stage,badgeBox;private TextView title,subtitle,expand;private int insetTop,insetBottom;
 private Widgets.Zoom zoom;private File pdf;private int page=0,pages=0,pageToken=0;private TextView pageLabel;private SeekBar pageSeek;private final LruCache<Integer,Bitmap> rendered=new LruCache<Integer,Bitmap>(5);
 private VideoView video;private MediaPlayer sound;private TextView playButton,timeLabel;private SeekBar seek;
 private final Handler handler=new Handler(Looper.getMainLooper());private final java.util.concurrent.ExecutorService worker=java.util.concurrent.Executors.newSingleThreadExecutor();
 private File work;

 private String t(String tr,String kr){return ku?kr:tr;}
 private int dp(float x){return ui.dp(x);}
 private int screenHeight(){return getResources().getDisplayMetrics().heightPixels;}

 @Override public void onCreate(Bundle state){SharedPreferences p=getSharedPreferences("MainActivity",0);ku=p.getBoolean("ku",false);String theme=p.getString("theme","system");
  int night=getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK;dark=theme.equals("dark")||(theme.equals("system")&&night==android.content.res.Configuration.UI_MODE_NIGHT_YES);
  ui=new Ui(this,dark,p.getInt("accent",0));super.onCreate(state);PDFBoxResourceLoader.init(this);
  work=new File(getCacheDir(),"quick");deleteTree(work);work.mkdirs();
  FrameLayout root=new FrameLayout(this);dim=new View(this);dim.setBackgroundColor(0x8C000000);dim.setOnClickListener(new View.OnClickListener(){public void onClick(View v){dismiss();}});root.addView(dim,new FrameLayout.LayoutParams(-1,-1));
  sheet=ui.column();sheet.setClickable(true);root.addView(sheet,new FrameLayout.LayoutParams(-1,sheetHeight(),Gravity.BOTTOM));
  View handle=new View(this);handle.setBackground(ui.round(ui.border,3,0));LinearLayout.LayoutParams hl=new LinearLayout.LayoutParams(dp(40),dp(5));hl.gravity=Gravity.CENTER_HORIZONTAL;hl.setMargins(0,dp(10),0,dp(6));sheet.addView(handle,hl);
  LinearLayout head=ui.row();head.setPadding(0,dp(4),0,dp(12));badgeBox=new FrameLayout(this);head.addView(badgeBox,new LinearLayout.LayoutParams(dp(44),dp(44)));
  LinearLayout names=ui.column();names.setPadding(dp(12),0,dp(4),0);title=ui.label("",16,ui.text,true);title.setSingleLine(true);title.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE);subtitle=ui.small("");subtitle.setSingleLine(true);
  names.addView(title);names.addView(subtitle);head.addView(names,new LinearLayout.LayoutParams(0,-2,1));
  expand=iconButton("expand",new View.OnClickListener(){public void onClick(View v){setFull(!full);}});head.addView(expand);
  head.addView(iconButton("close",new View.OnClickListener(){public void onClick(View v){dismiss();}}));sheet.addView(head);
  // Everything under the title scrolls: the big preview first, then the format ring and the tools.
  body=new ScrollView(this);body.setVerticalScrollBarEnabled(false);body.setOverScrollMode(View.OVER_SCROLL_NEVER);LinearLayout inner=ui.column();body.addView(inner);sheet.addView(body,new LinearLayout.LayoutParams(-1,0,1));
  stage=new FrameLayout(this);stage.setBackground(ui.round(dark?0xFF0E0D12:0xFFE9E7EF,18,0));stage.setClipToOutline(true);inner.addView(stage,new LinearLayout.LayoutParams(-1,stageHeight()));
  controls=ui.column();controls.setPadding(0,dp(6),0,0);controls.setVisibility(View.GONE);inner.addView(controls);
  shortcuts=ui.column();inner.addView(shortcuts);
  View.OnTouchListener drag=dragToClose();handle.setOnTouchListener(drag);names.setOnTouchListener(drag);badgeBox.setOnTouchListener(drag);
  setContentView(root);
  Window w=getWindow();w.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION|(dark?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR));
  w.getDecorView().setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener(){public WindowInsets onApplyWindowInsets(View v,WindowInsets i){insetTop=i.getSystemWindowInsetTop();insetBottom=i.getSystemWindowInsetBottom();
   int l=i.getSystemWindowInsetLeft(),r=i.getSystemWindowInsetRight();FrameLayout.LayoutParams lp=(FrameLayout.LayoutParams)sheet.getLayoutParams();lp.leftMargin=l;lp.rightMargin=r;sheet.setLayoutParams(lp);pad();return i;}});
  w.getDecorView().requestApplyInsets();pad();
  sheet.setVisibility(View.INVISIBLE);dim.setAlpha(0f);
  sheet.post(new Runnable(){public void run(){sheet.setTranslationY(sheet.getHeight()+dp(40));sheet.setVisibility(View.VISIBLE);sheet.animate().translationY(0).setDuration(300).setInterpolator(new DecelerateInterpolator(1.8f)).start();dim.animate().alpha(1f).setDuration(260).start();}});
  open(getIntent());}
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);release();stage.removeAllViews();controls.removeAllViews();controls.setVisibility(View.GONE);rendered.evictAll();pdf=null;open(i);}
 @Override protected void onPause(){super.onPause();if(video!=null&&video.isPlaying()){video.pause();icon();}if(sound!=null&&sound.isPlaying()){sound.pause();icon();}}
 @Override protected void onDestroy(){release();worker.shutdownNow();deleteTree(work);super.onDestroy();}
 @Override public void onBackPressed(){if(full)setFull(false);else dismiss();}
 @Override public void onConfigurationChanged(android.content.res.Configuration c){super.onConfigurationChanged(c);sheet.getLayoutParams().height=sheetHeight();stage.getLayoutParams().height=stageHeight();sheet.requestLayout();}
 private void release(){handler.removeCallbacksAndMessages(null);if(video!=null){video.stopPlayback();video=null;}if(sound!=null){sound.release();sound=null;}}

 // ---------------------------------------------------------------- the panel
 private int stageHeight(){int h=screenHeight();if(full)return Math.max(dp(200),h-insetTop-insetBottom-dp(controls!=null&&controls.getVisibility()==View.VISIBLE?190:110));
  return kind.equals("audio")?dp(170):kind.equals("image")||kind.equals("text")?(int)(h*0.56f):(int)(h*0.64f);}
 /** The frame takes the picture's shape: a wide video gets no empty black bands, a page stays tall. */
 private void fitStage(int w,int h){if(full||w<=0||h<=0)return;int width=stage.getWidth()>0?stage.getWidth():getResources().getDisplayMetrics().widthPixels-dp(32);
  int want=Math.max(dp(200),Math.min(stageHeight(),Math.round((float)width*h/w)));if(stage.getLayoutParams().height!=want){stage.getLayoutParams().height=want;stage.requestLayout();}}
 /** The panel takes most of the screen; the file list stays visible above it. */
 private int sheetHeight(){return full?-1:(int)(screenHeight()*0.93f);}
 private void pad(){sheet.setPadding(dp(16),full?insetTop:0,dp(16),insetBottom+dp(12));
  float r=full?0:dp(26);GradientDrawable g=new GradientDrawable();g.setColor(ui.surface);g.setCornerRadii(new float[]{r,r,r,r,0,0,0,0});sheet.setBackground(g);}
 /** Panel or the whole screen; the picture keeps its place, only the frame grows. */
 private void setFull(boolean on){full=on;FrameLayout.LayoutParams lp=(FrameLayout.LayoutParams)sheet.getLayoutParams();lp.height=sheetHeight();sheet.setLayoutParams(lp);
  stage.getLayoutParams().height=stageHeight();stage.requestLayout();body.scrollTo(0,0);
  expand.setCompoundDrawablesRelative(ui.icon(on?"collapse":"expand",ui.text,22),null,null,null);pad();
  getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION|(dark?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR|(on?View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR:0)));}
 private void dismiss(){if(closing)return;closing=true;if(video!=null)video.pause();if(sound!=null)try{sound.pause();}catch(Exception ignored){}
  sheet.animate().translationY(sheet.getHeight()+dp(40)).setDuration(220).setInterpolator(new android.view.animation.AccelerateInterpolator()).start();
  dim.animate().alpha(0f).setDuration(220).withEndAction(new Runnable(){public void run(){finish();overridePendingTransition(0,0);}}).start();}
 /** Pulling the handle or the title down moves the panel with the finger; far enough (or quick enough) closes it. */
 private View.OnTouchListener dragToClose(){return new View.OnTouchListener(){float startY,lastY;long lastT;float speed;
  public boolean onTouch(View v,MotionEvent e){switch(e.getActionMasked()){
   case MotionEvent.ACTION_DOWN:startY=lastY=e.getRawY();lastT=e.getEventTime();speed=0;sheet.animate().cancel();return true;
   case MotionEvent.ACTION_MOVE:{float dy=Math.max(0,e.getRawY()-startY);long dt=Math.max(1,e.getEventTime()-lastT);speed=(e.getRawY()-lastY)/dt;lastY=e.getRawY();lastT=e.getEventTime();
    sheet.setTranslationY(dy);dim.setAlpha(1f-Math.min(0.8f,dy/Math.max(1,sheet.getHeight())));return true;}
   case MotionEvent.ACTION_UP:case MotionEvent.ACTION_CANCEL:{float dy=e.getRawY()-startY;
    if(dy>sheet.getHeight()*0.25f||speed>1.2f)dismiss();
    else if(Math.abs(dy)<dp(6)&&e.getActionMasked()==MotionEvent.ACTION_UP&&v!=badgeBox){sheet.setTranslationY(0);dim.setAlpha(1f);}
    else{sheet.animate().translationY(0).setDuration(200).setInterpolator(new DecelerateInterpolator()).start();dim.animate().alpha(1f).setDuration(200).start();}return true;}}
   return false;}};}

 private TextView iconButton(String icon,View.OnClickListener l){TextView b=new TextView(this);b.setCompoundDrawablesRelative(ui.icon(icon,ui.text,22),null,null,null);b.setPadding(dp(10),dp(10),dp(10),dp(10));
  b.setBackground(ui.ripple(ui.round(0,22,0),22));b.setOnClickListener(l);b.setClickable(true);return b;}
 private View roundButton(String icon,String label,View.OnClickListener l){FrameLayout f=new FrameLayout(this);f.setBackground(ui.ripple(ui.round(ui.accentSoft,24,0),24));f.setContentDescription(label);f.setOnClickListener(l);f.setClickable(true);
  ImageView i=new ImageView(this);i.setImageDrawable(ui.icon(icon,ui.accentText,22));f.addView(i,new FrameLayout.LayoutParams(dp(22),dp(22),Gravity.CENTER));
  LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(dp(48),dp(48));lp.setMargins(dp(10),0,0,0);f.setLayoutParams(lp);return f;}
 private void message(String text,boolean spinner){stage.removeAllViews();LinearLayout c=ui.column();c.setGravity(Gravity.CENTER);c.setPadding(dp(28),0,dp(28),0);
  if(spinner){ProgressBar p=new ProgressBar(this);p.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(ui.accent));c.addView(p);c.addView(ui.space(12));}
  else{c.addView(ui.badge("doc",64,ui.surface2,ui.muted));c.addView(ui.space(14));}
  TextView m=ui.body(text);m.setGravity(Gravity.CENTER);c.addView(m);stage.addView(c,new FrameLayout.LayoutParams(-1,-1));}
 private void fail(final String why){runOnUiThread(new Runnable(){public void run(){if(!isFinishing())message(why,false);}});}

 // ---------------------------------------------------------------- what the file is
 private void open(Intent in){uri=in==null?null:in.getData();if(uri==null&&in!=null&&Intent.ACTION_SEND.equals(in.getAction()))uri=in.getParcelableExtra(Intent.EXTRA_STREAM);
  if(uri==null){finish();return;}
  mime=in.getType();try{if(mime==null)mime=getContentResolver().getType(uri);}catch(Exception ignored){}if(mime==null)mime="";
  name=uri.getLastPathSegment()==null?"dosya":uri.getLastPathSegment();size=-1;
  try{Cursor c=getContentResolver().query(uri,null,null,null,null);if(c!=null)try{if(c.moveToFirst()){int n=c.getColumnIndex(OpenableColumns.DISPLAY_NAME);if(n>=0&&c.getString(n)!=null)name=c.getString(n);int s=c.getColumnIndex(OpenableColumns.SIZE);if(s>=0&&!c.isNull(s))size=c.getLong(s);}}finally{c.close();}}catch(Exception ignored){}
  if(name.contains("/"))name=name.substring(name.lastIndexOf('/')+1);
  ext=name.contains(".")?name.substring(name.lastIndexOf('.')+1).toLowerCase(Locale.ROOT):"";
  kind=IMAGES.contains(ext)||mime.startsWith("image/")?"image":VIDEOS.contains(ext)||mime.startsWith("video/")?"video":SOUNDS.contains(ext)||mime.startsWith("audio/")||mime.equals("application/ogg")?"audio"
   :ext.equals("pdf")||mime.equals("application/pdf")?"pdf":DOCS.contains(ext)?"doc":TEXTS.contains(ext)||mime.startsWith("text/")?"text":"other";
  title.setText(name);subtitle.setText(describe(null));badgeBox.removeAllViews();
  FrameLayout b=ui.badge(kind.equals("image")?"image":kind.equals("video")?"video":kind.equals("audio")?"audio":kind.equals("text")?"text":"doc",44,ui.accentSoft,ui.accentText);b.setLayoutParams(new FrameLayout.LayoutParams(-1,-1));badgeBox.addView(b);
  stage.setBackground(ui.round(dark?0xFF0E0D12:0xFFE9E7EF,18,0));stage.getLayoutParams().height=stageHeight();shortcuts.removeAllViews();body.scrollTo(0,0);
  loadShortcuts();
  if(kind.equals("video"))showVideo();else if(kind.equals("audio"))showSound();
  else if(kind.equals("other"))message(t("Bu dosya türü önizlenemiyor.\nAşağıdan Dönüştürücü'de açıp başka biçime çevirebilirsin.","Ev cureyê dosyeyê nayê pêşdîtin.\nBi \"Veguherîne\" dikarî biguherînî."),false);
  else{message(kind.equals("doc")?t("Belge hazırlanıyor…","Belge tê amadekirin…"):t("Açılıyor…","Tê vekirin…"),true);
   worker.execute(new Runnable(){public void run(){try{File f=copy();
    if(kind.equals("image")){final Bitmap b=Tools.load(f,4096);runOnUiThread(new Runnable(){public void run(){showPicture(b);subtitle.setText(describe(b.getWidth()+" × "+b.getHeight()));}});}
    else if(kind.equals("text")){final String s=DocumentEngine.read(f,ext.equals("srt")||ext.equals("vtt")||ext.equals("log")||ext.equals("json")||ext.equals("xml")?"txt":ext);runOnUiThread(new Runnable(){public void run(){showText(s);}});}
    else{File doc=kind.equals("pdf")?f:toPdf(f);pdf=doc;pages=Tools.pageCount(doc);if(pages<1)throw new IOException("empty");final Bitmap b=pageBitmap(0);
     runOnUiThread(new Runnable(){public void run(){showPages(b);}});}}
   catch(Throwable e){fail(t("Dosya açılamadı. Bozuk ya da desteklenmeyen olabilir.","Dosye venebû. Dibe ku xera be an nayê destekirin."));}}});}}
 private String describe(String extra){StringBuilder s=new StringBuilder(ext.isEmpty()?kind.toUpperCase(Locale.ROOT):ext.toUpperCase(Locale.ROOT));
  if(size>=0)s.append(" · ").append(size>=1<<20?String.format(Locale.ROOT,"%.1f MB",size/1048576.0):Math.max(1,size/1024)+" KB");if(extra!=null)s.append(" · ").append(extra);return s.toString();}
 private File copy()throws IOException{File f=new File(work,"file."+(ext.isEmpty()?"bin":ext));InputStream in=getContentResolver().openInputStream(uri);if(in==null)throw new IOException("unreadable");
  try{OutputStream o=new FileOutputStream(f);try{byte[]b=new byte[65536];int n;while((n=in.read(b))>0){if(Thread.interrupted())throw new InterruptedIOException();o.write(b,0,n);}}finally{o.close();}}finally{in.close();}return f;}
 /** Office files, e-books and web pages are laid out as PDF pages, like the workspace shows them. */
 private File toPdf(File src)throws Exception{File dir=new File(work,"pdf");dir.mkdirs();RichDocument.Host host=new RichDocument.Host(){public void check()throws Exception{if(Thread.interrupted())throw new InterruptedException();}};
  try{if(Arrays.asList("docx","odt","epub","html","htm").contains(ext))return RichDocument.read(src,ext,host).write("pdf",dir,host);}catch(Exception rich){}
  return DocumentEngine.write(DocumentEngine.read(src,ext),"pdf",dir);}

 // ---------------------------------------------------------------- pictures and pages
 private Widgets.Zoom zoomView(){zoom=new Widgets.Zoom(this);zoom.listener=new Widgets.Zoom.Listener(){public void tap(){}public void turn(int d){turnPage(d);}};return zoom;}
 private void showPicture(Bitmap b){fitStage(b.getWidth(),b.getHeight());stage.removeAllViews();stage.addView(zoomView(),new FrameLayout.LayoutParams(-1,-1));zoom.show(b,0);}
 private int renderWidth(){android.util.DisplayMetrics m=getResources().getDisplayMetrics();return Math.min(2400,Math.max(m.widthPixels,m.heightPixels*3/4)*3/2);}
 private Bitmap pageBitmap(int i)throws IOException{Bitmap b=rendered.get(i);if(b==null){b=Tools.renderPage(pdf,i,renderWidth());rendered.put(i,b);}return b;}
 private void showPages(Bitmap first){fitStage(first.getWidth(),first.getHeight());stage.removeAllViews();stage.addView(zoomView(),new FrameLayout.LayoutParams(-1,-1));zoom.show(first,0);page=0;subtitle.setText(describe(pages+t(" sayfa"," rûpel")));
  controls.removeAllViews();LinearLayout r=ui.row();
  r.addView(iconButton("chevron_left",new View.OnClickListener(){public void onClick(View v){turnPage(-1);}}));
  pageLabel=ui.label("",14,ui.text,true);pageLabel.setGravity(Gravity.CENTER);r.addView(pageLabel,new LinearLayout.LayoutParams(0,-2,1));
  r.addView(iconButton("chevron",new View.OnClickListener(){public void onClick(View v){turnPage(1);}}));controls.addView(r);
  pageSeek=null;if(pages>2){pageSeek=new SeekBar(this);pageSeek.setMax(pages-1);tint(pageSeek);pageSeek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
   public void onProgressChanged(SeekBar s,int v,boolean user){if(user)pageLabel.setText(pageText(v));}public void onStartTrackingTouch(SeekBar s){}
   public void onStopTrackingTouch(SeekBar s){goPage(s.getProgress(),s.getProgress()>page?1:-1);}});controls.addView(pageSeek);}
  controls.setVisibility(View.VISIBLE);pageLabel.setText(pageText(0));prefetch(1);}
 private String pageText(int i){return t("Sayfa ","Rûpel ")+(i+1)+" / "+pages;}
 private void turnPage(int d){if(pdf==null)return;int to=page+d;if(to<0||to>=pages){zoom.animate().translationX(-d*dp(18)).setDuration(90).withEndAction(new Runnable(){public void run(){zoom.animate().translationX(0).setDuration(140);}});return;}goPage(to,d);}
 private void goPage(final int to,final int dir){if(to==page||pdf==null)return;page=to;pageLabel.setText(pageText(to));if(pageSeek!=null)pageSeek.setProgress(to);final int token=++pageToken;
  Bitmap ready=rendered.get(to);if(ready!=null){zoom.show(ready,dir);prefetch(to+dir);return;}
  worker.execute(new Runnable(){public void run(){try{final Bitmap b=pageBitmap(to);runOnUiThread(new Runnable(){public void run(){if(token==pageToken){zoom.show(b,dir);prefetch(to+dir);}}});}catch(Exception ignored){}}});}
 /** The page after the one shown is drawn ahead, so turning to it is instant. */
 private void prefetch(final int i){if(pdf==null||i<0||i>=pages||rendered.get(i)!=null)return;worker.execute(new Runnable(){public void run(){try{pageBitmap(i);}catch(Exception ignored){}}});}

 // ---------------------------------------------------------------- text
 private void showText(String s){stage.removeAllViews();ScrollView sc=new ScrollView(this);TextView tv=ui.label(s.length()>400000?s.substring(0,400000)+"\n…":s,14.5f,ui.text,false);
  if(Arrays.asList("csv","tsv","json","xml","log","srt","vtt").contains(ext))tv.setTypeface(Typeface.MONOSPACE);tv.setTextIsSelectable(true);
  tv.setPadding(dp(16),dp(14),dp(16),dp(14));sc.addView(tv);stage.setBackground(ui.round(ui.surface2,18,0));stage.addView(sc,new FrameLayout.LayoutParams(-1,-1));
  subtitle.setText(describe(s.split("\n",-1).length+t(" satır"," rêz")));}

 // ---------------------------------------------------------------- video and sound
 private void showVideo(){stage.removeAllViews();stage.setBackground(ui.round(0xFF000000,18,0));video=new VideoView(this);final VideoView v=video;stage.addView(v,new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER));
  View catcher=new View(this);catcher.setOnClickListener(new View.OnClickListener(){public void onClick(View x){if(playButton!=null)playButton.performClick();}});stage.addView(catcher,new FrameLayout.LayoutParams(-1,-1));
  mediaControls();
  v.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer mp){fitStage(mp.getVideoWidth(),mp.getVideoHeight());seek.setMax(Math.max(1,v.getDuration()));subtitle.setText(describe(mp.getVideoWidth()+"×"+mp.getVideoHeight()+" · "+MainActivity.clock(v.getDuration()/1000.0)));v.start();tick();}});
  v.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer mp){icon();}});
  v.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer mp,int a,int b){release();stage.setBackground(ui.round(dark?0xFF0E0D12:0xFFE9E7EF,18,0));message(t("Bu video telefonun oynatıcısıyla gösterilemiyor.\nAşağıdan MP4'e dönüştürebilirsin.","Ev vîdyo bi lîstikvana telefonê nayê nîşandan.\nBi \"Veguherîne\" dikarî bikî MP4."),false);controls.setVisibility(View.GONE);return true;}});
  v.setVideoURI(uri);}
 private void showSound(){stage.removeAllViews();LinearLayout c=ui.column();c.setGravity(Gravity.CENTER);c.addView(ui.badge("audio",84,ui.accentSoft,ui.accentText));stage.addView(c,new FrameLayout.LayoutParams(-1,-1));
  mediaControls();sound=new MediaPlayer();final MediaPlayer mp=sound;
  try{mp.setDataSource(this,uri);mp.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer x){seek.setMax(Math.max(1,x.getDuration()));subtitle.setText(describe(MainActivity.clock(x.getDuration()/1000.0)));x.start();tick();}});
   mp.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer x){icon();}});
   mp.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer x,int a,int b){release();message(t("Bu ses telefonda çalınamıyor.\nAşağıdan MP3'e dönüştürebilirsin.","Ev deng li telefonê nayê lêdan.\nBi \"Veguherîne\" dikarî bikî MP3."),false);controls.setVisibility(View.GONE);return true;}});
   mp.prepareAsync();}catch(Exception e){release();message(t("Bu ses telefonda çalınamıyor.","Ev deng li telefonê nayê lêdan."),false);}}
 private boolean playing(){try{return video!=null?video.isPlaying():sound!=null&&sound.isPlaying();}catch(Exception e){return false;}}
 private int position(){try{return video!=null?video.getCurrentPosition():sound!=null?sound.getCurrentPosition():0;}catch(Exception e){return 0;}}
 private int duration(){try{return video!=null?video.getDuration():sound!=null?sound.getDuration():0;}catch(Exception e){return 0;}}
 private void seekTo(int ms){try{if(video!=null)video.seekTo(ms);else if(sound!=null)sound.seekTo(ms);}catch(Exception ignored){}}
 private void mediaControls(){controls.removeAllViews();LinearLayout r=ui.row();playButton=iconButton("pause",new View.OnClickListener(){public void onClick(View v){
   try{if(playing()){if(video!=null)video.pause();else sound.pause();}else{if(video!=null)video.start();else if(sound!=null)sound.start();tick();}}catch(Exception ignored){}icon();}});
  seek=new SeekBar(this);tint(seek);timeLabel=ui.small("0:00 / 0:00");r.addView(playButton);r.addView(seek,new LinearLayout.LayoutParams(0,-2,1));r.addView(timeLabel);controls.addView(r);
  seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int v,boolean user){if(user){seekTo(v);time(v);}}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});
  controls.setVisibility(View.VISIBLE);}
 private void time(int pos){timeLabel.setText(MainActivity.tclock(pos/1000.0)+" / "+MainActivity.clock(duration()/1000.0));}
 private void icon(){if(playButton!=null)playButton.setCompoundDrawablesRelative(ui.icon(playing()?"pause":"play",ui.text,26),null,null,null);}
 private final Runnable ticker=new Runnable(){public void run(){if(seek==null)return;int p=position();seek.setProgress(p);time(p);icon();if(playing())handler.postDelayed(this,200);}};
 private void tick(){handler.removeCallbacks(ticker);handler.post(ticker);}
 private void tint(SeekBar s){s.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent));s.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(ui.dark?0xFF55516A:0xFFB9B5C9));s.setThumbTintList(android.content.res.ColorStateList.valueOf(ui.accent));}

 // ---------------------------------------------------------------- shortcuts: the format ring and the tools
 /** Name the workspace uses for this kind of file. */
 private String engineExt(){if(kind.equals("image"))return "image";if(kind.equals("pdf"))return "pdf";if(kind.equals("doc"))return ext;
  if(kind.equals("text"))return Arrays.asList("srt","md","csv","tsv","rst").contains(ext)?ext:"txt";return ext;}
 /** Sound and video need to know their tracks first (a video without sound offers no MP3). */
 private void loadShortcuts(){final Uri u=uri;
  if(kind.equals("other")){LinearLayout row=ui.row();row.setPadding(0,dp(14),0,0);row.addView(ui.button(t("Dönüştürücüde aç","Di Veguherînerê de veke"),"wand",0,new View.OnClickListener(){public void onClick(View v){toWorkspace(null,null);}}),new LinearLayout.LayoutParams(0,-2,1));
   row.addView(roundButton("share",t("Paylaş","Parve bike"),new View.OnClickListener(){public void onClick(View v){share();}}));row.addView(roundButton("open",t("Başka uygulamayla aç","Bi sepaneke din veke"),new View.OnClickListener(){public void onClick(View v){openElsewhere();}}));shortcuts.addView(row);return;}
  if(!kind.equals("video")&&!kind.equals("audio")){fillShortcuts(null);return;}
  worker.execute(new Runnable(){public void run(){final MediaEngine.Info in=new MediaEngine.Info();android.media.MediaMetadataRetriever r=new android.media.MediaMetadataRetriever();
   try{r.setDataSource(QuickView.this,u);in.video=kind.equals("video")&&!"no".equals(r.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO));
    String a=r.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_HAS_AUDIO);in.audio=a==null?!in.video:"yes".equals(a);}
   catch(Exception e){in.video=kind.equals("video");in.audio=true;}finally{try{r.release();}catch(Exception ignored){}}
   runOnUiThread(new Runnable(){public void run(){if(u==uri&&!isFinishing())fillShortcuts(in);}});}});}
 private void fillShortcuts(MediaEngine.Info in){shortcuts.removeAllViews();String e=engineExt();
  final String[] all=MainActivity.formatValues(in,e),front=MainActivity.frontFormats(in,e),back=Arrays.copyOfRange(all,front.length,all.length);
  if(!Arrays.asList(all).contains(chosen))chosen=all[0];
  LinearLayout card=ui.card();card.setGravity(Gravity.CENTER_HORIZONTAL);LinearLayout.LayoutParams cl=new LinearLayout.LayoutParams(-1,-2);cl.setMargins(0,dp(14),0,0);
  TextView head=ui.label(t("Neye dönüştürülsün?","Bibe çi formatê?"),17,ui.text,true);head.setLayoutParams(new LinearLayout.LayoutParams(-1,-2));card.addView(head);
  final Widgets.Donut d=new Widgets.Donut(this,ui);String src=in!=null?(in.video?t("video","vîdyo"):t("ses","deng")):kind.equals("image")?t("fotoğraf","wêne"):ext.toUpperCase(Locale.ROOT);
  d.set(front,back,chosen,"1 "+src,"→ "+chosen);
  d.listener=new Widgets.Donut.Listener(){public void chosen(String f){chosen=f;d.hint="→ "+f;d.invalidate();goButton.setText(t(f+" olarak dönüştür",f+" veguherîne"));}public void flipped(boolean b){}};
  card.addView(d,new LinearLayout.LayoutParams(-1,-2));
  if(back.length>0){TextView h=ui.small(t("Diğer biçimler için ortaya dokun.","Ji bo formatên din li navendê bitikîne."));h.setGravity(Gravity.CENTER);card.addView(h,new LinearLayout.LayoutParams(-1,-2));}
  LinearLayout row=ui.row();row.setPadding(0,dp(12),0,0);
  goButton=ui.button(t(chosen+" olarak dönüştür",chosen+" veguherîne"),"wand",0,new View.OnClickListener(){public void onClick(View v){toWorkspace("convert",chosen);}});row.addView(goButton,new LinearLayout.LayoutParams(0,-2,1));
  row.addView(roundButton("share",t("Paylaş","Parve bike"),new View.OnClickListener(){public void onClick(View v){share();}}));
  row.addView(roundButton("open",t("Başka uygulamayla aç","Bi sepaneke din veke"),new View.OnClickListener(){public void onClick(View v){openElsewhere();}}));
  card.addView(row,new LinearLayout.LayoutParams(-1,-2));shortcuts.addView(card,cl);
  List<String[]> acts=MainActivity.offeredActions(in,e);
  if(acts.size()>1){shortcuts.addView(ui.section(t("Araçlar","Amûr")));Ui.Flow f=ui.flow();
   for(final String[] a:acts){if(a[0].equals("convert"))continue;TextView c=ui.chip(ku?a[2]:a[1],false,new View.OnClickListener(){public void onClick(View v){toWorkspace(a[0],null);}});
    c.setCompoundDrawablesRelative(ui.icon(a[3],ui.accentText,18),null,null,null);c.setCompoundDrawablePadding(dp(6));f.addView(c);}
   shortcuts.addView(f);}
  shortcuts.addView(ui.space(8));}

 // ---------------------------------------------------------------- actions
 private void toWorkspace(String action,String format){try{Intent i=new Intent(this,MainActivity.class);i.setAction(Intent.ACTION_VIEW);i.setDataAndType(uri,mime.isEmpty()?"*/*":mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
   if(action!=null){i.putExtra("quick_action",action);if(format!=null)i.putExtra("quick_format",format);}startActivity(i);finish();}
  catch(Exception e){Toast.makeText(this,t("Açılamadı.","Venebû."),Toast.LENGTH_SHORT).show();}}
 private void share(){try{Intent i=new Intent(Intent.ACTION_SEND);i.setType(mime.isEmpty()?"*/*":mime);i.putExtra(Intent.EXTRA_STREAM,uri);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,t("Paylaş","Parve bike")));}
  catch(Exception e){Toast.makeText(this,t("Paylaşılamadı.","Nehat parvekirin."),Toast.LENGTH_SHORT).show();}}
 /** Another viewer or editor; this app's own entries are left out of the list. */
 private void openElsewhere(){try{Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,mime.isEmpty()?"*/*":mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
   Intent c=Intent.createChooser(i,t("Başka uygulamayla aç","Bi sepaneke din veke"));c.putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS,new ComponentName[]{new ComponentName(this,QuickView.class),new ComponentName(this,MainActivity.class)});startActivity(c);}
  catch(Exception e){Toast.makeText(this,t("Bu dosyayı açabilecek başka uygulama yok.","Sepaneke din tune ku vê dosyeyê veke."),Toast.LENGTH_SHORT).show();}}
 static void deleteTree(File f){if(f==null||!f.exists())return;File[] k=f.listFiles();if(k!=null)for(File x:k)deleteTree(x);f.delete();}
}
