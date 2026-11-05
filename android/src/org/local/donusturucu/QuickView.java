package org.local.donusturucu;
import android.app.Activity;import android.content.*;import android.database.Cursor;import android.graphics.*;import android.graphics.drawable.*;import android.media.MediaPlayer;import android.net.Uri;import android.os.*;import android.provider.OpenableColumns;import android.util.LruCache;import android.view.*;import android.widget.*;
import java.io.*;import java.util.*;
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader;

/** Quick look: a tap on a file in the file manager shows it at once (picture, pages, video, sound or text)
 *  without opening the whole app; "Dönüştür" takes it on to the workspace. */
public class QuickView extends Activity {
 static final List<String> IMAGES=Arrays.asList("jpg","jpeg","jfif","png","webp","bmp","gif","heic","heif");
 static final List<String> VIDEOS=Arrays.asList("mp4","m4v","mkv","webm","mov","3gp","avi","ts","mpg","mpeg");
 static final List<String> SOUNDS=Arrays.asList("mp3","m4a","aac","wav","ogg","oga","opus","flac","amr","wma","mka");
 static final List<String> TEXTS=Arrays.asList("txt","srt","vtt","md","csv","tsv","rst","log","json","xml");
 static final List<String> DOCS=Arrays.asList("docx","odt","epub","html","htm","rtf","pptx","odp","xlsx");

 private Ui ui;private boolean ku;private Uri uri;private String mime,name="",ext="",kind="";private long size=-1;
 private FrameLayout stage;private LinearLayout top,bottom;private TextView title,subtitle;private boolean barsShown=true;
 private Widgets.Zoom zoom;private File pdf;private int page=0,pages=0,pageToken=0;private TextView pageLabel;private SeekBar pageSeek;private final LruCache<Integer,Bitmap> rendered=new LruCache<Integer,Bitmap>(5);
 private VideoView video;private MediaPlayer sound;private TextView playButton,timeLabel;private SeekBar seek;
 private final Handler handler=new Handler(Looper.getMainLooper());private final java.util.concurrent.ExecutorService worker=java.util.concurrent.Executors.newSingleThreadExecutor();
 private File work;

 private String t(String tr,String kr){return ku?kr:tr;}
 private int dp(float x){return ui.dp(x);}

 @Override public void onCreate(Bundle state){SharedPreferences p=getSharedPreferences("MainActivity",0);ku=p.getBoolean("ku",false);ui=new Ui(this,true,p.getInt("accent",0));
  super.onCreate(state);PDFBoxResourceLoader.init(this);
  Window w=getWindow();w.setBackgroundDrawable(new ColorDrawable(0xFF000000));w.setStatusBarColor(0xFF000000);w.setNavigationBarColor(0xFF000000);w.getDecorView().setSystemUiVisibility(0);
  work=new File(getCacheDir(),"quick");deleteTree(work);work.mkdirs();
  FrameLayout root=new FrameLayout(this);root.setBackgroundColor(0xFF000000);stage=new FrameLayout(this);root.addView(stage,new FrameLayout.LayoutParams(-1,-1));
  top=ui.row();top.setPadding(dp(6),dp(6),dp(10),dp(14));top.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,new int[]{0xE6000000,0x00000000}));
  top.addView(iconButton("close",new View.OnClickListener(){public void onClick(View v){finish();}}));
  LinearLayout names=ui.column();names.setPadding(dp(4),0,dp(8),0);title=ui.label("",16,0xFFFFFFFF,true);title.setSingleLine(true);title.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE);subtitle=ui.label("",12,0xB3FFFFFF,false);subtitle.setSingleLine(true);
  names.addView(title);names.addView(subtitle);top.addView(names,new LinearLayout.LayoutParams(0,-2,1));
  top.addView(iconButton("share",new View.OnClickListener(){public void onClick(View v){share();}}));
  top.addView(iconButton("open",new View.OnClickListener(){public void onClick(View v){openElsewhere();}}));
  TextView go=ui.button(t("Dönüştür","Veguherîne"),"wand",0,new View.OnClickListener(){public void onClick(View v){toWorkspace();}});go.setMinHeight(dp(40));go.setPadding(dp(14),dp(8),dp(16),dp(8));
  LinearLayout.LayoutParams gl=new LinearLayout.LayoutParams(-2,-2);gl.setMargins(dp(4),0,0,0);top.addView(go,gl);
  root.addView(top,new FrameLayout.LayoutParams(-1,-2,Gravity.TOP));
  bottom=ui.column();bottom.setPadding(dp(14),dp(18),dp(14),dp(10));bottom.setBackground(new GradientDrawable(GradientDrawable.Orientation.BOTTOM_TOP,new int[]{0xE6000000,0x00000000}));bottom.setVisibility(View.GONE);
  root.addView(bottom,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));
  setContentView(root);
  w.getDecorView().setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener(){public WindowInsets onApplyWindowInsets(View v,WindowInsets i){
   top.setPadding(i.getSystemWindowInsetLeft()+dp(6),i.getSystemWindowInsetTop()+dp(6),i.getSystemWindowInsetRight()+dp(10),dp(14));
   bottom.setPadding(i.getSystemWindowInsetLeft()+dp(14),dp(18),i.getSystemWindowInsetRight()+dp(14),i.getSystemWindowInsetBottom()+dp(10));return i;}});
  w.getDecorView().requestApplyInsets();
  open(getIntent());}
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);release();stage.removeAllViews();bottom.removeAllViews();bottom.setVisibility(View.GONE);rendered.evictAll();pdf=null;open(i);}
 @Override protected void onPause(){super.onPause();if(video!=null&&video.isPlaying()){video.pause();icon();}if(sound!=null&&sound.isPlaying()){sound.pause();icon();}}
 @Override protected void onDestroy(){release();worker.shutdownNow();deleteTree(work);super.onDestroy();}
 private void release(){handler.removeCallbacksAndMessages(null);if(video!=null){video.stopPlayback();video=null;}if(sound!=null){sound.release();sound=null;}}

 private TextView iconButton(String icon,View.OnClickListener l){TextView b=new TextView(this);b.setCompoundDrawablesRelative(ui.icon(icon,0xFFFFFFFF,22),null,null,null);b.setPadding(dp(10),dp(10),dp(10),dp(10));
  b.setBackground(ui.ripple(ui.round(0,22,0),22));b.setOnClickListener(l);b.setClickable(true);return b;}
 private void message(String text,boolean spinner){stage.removeAllViews();LinearLayout c=ui.column();c.setGravity(Gravity.CENTER);c.setPadding(dp(32),0,dp(32),0);
  if(spinner){ProgressBar p=new ProgressBar(this);p.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(ui.accent));c.addView(p);c.addView(ui.space(14));}
  else{FrameLayout b=ui.badge(kind.equals("audio")?"audio":"doc",72,0xFF24222C,ui.accent);c.addView(b);c.addView(ui.space(16));}
  TextView m=ui.label(text,15,0xDDFFFFFF,false);m.setGravity(Gravity.CENTER);c.addView(m);
  if(!spinner){c.addView(ui.space(20));c.addView(ui.button(t("Dönüştürücüde aç","Di Veguherînerê de veke"),"wand",0,new View.OnClickListener(){public void onClick(View v){toWorkspace();}}),new LinearLayout.LayoutParams(-2,-2));}
  stage.addView(c,new FrameLayout.LayoutParams(-1,-1));}
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
  title.setText(name);subtitle.setText(describe(null));
  if(kind.equals("video"))showVideo();else if(kind.equals("audio"))showSound();
  else if(kind.equals("other"))message(t("Bu dosya türü önizlenemiyor.\nDönüştürücüde açıp başka biçime çevirebilirsin.","Ev cureyê dosyeyê nayê pêşdîtin.\nDikarî di Veguherînerê de veke û biguherînî."),false);
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
 private Widgets.Zoom zoomView(){zoom=new Widgets.Zoom(this);zoom.listener=new Widgets.Zoom.Listener(){public void tap(){toggleBars();}public void turn(int d){turnPage(d);}};return zoom;}
 private void showPicture(Bitmap b){stage.removeAllViews();stage.addView(zoomView(),new FrameLayout.LayoutParams(-1,-1));zoom.show(b,0);}
 private int renderWidth(){android.util.DisplayMetrics m=getResources().getDisplayMetrics();return Math.min(2400,Math.max(m.widthPixels,m.heightPixels*3/4)*3/2);}
 private Bitmap pageBitmap(int i)throws IOException{Bitmap b=rendered.get(i);if(b==null){b=Tools.renderPage(pdf,i,renderWidth());rendered.put(i,b);}return b;}
 private void showPages(Bitmap first){stage.removeAllViews();stage.addView(zoomView(),new FrameLayout.LayoutParams(-1,-1));zoom.show(first,0);page=0;subtitle.setText(describe(pages+t(" sayfa"," rûpel")));
  bottom.removeAllViews();LinearLayout r=ui.row();
  r.addView(iconButton("chevron_left",new View.OnClickListener(){public void onClick(View v){turnPage(-1);}}));
  pageLabel=ui.label("",14,0xFFFFFFFF,true);pageLabel.setGravity(Gravity.CENTER);r.addView(pageLabel,new LinearLayout.LayoutParams(0,-2,1));
  r.addView(iconButton("chevron",new View.OnClickListener(){public void onClick(View v){turnPage(1);}}));bottom.addView(r);
  pageSeek=null;if(pages>2){pageSeek=new SeekBar(this);pageSeek.setMax(pages-1);tint(pageSeek);pageSeek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
   public void onProgressChanged(SeekBar s,int v,boolean user){if(user)pageLabel.setText(pageText(v));}public void onStartTrackingTouch(SeekBar s){}
   public void onStopTrackingTouch(SeekBar s){goPage(s.getProgress(),s.getProgress()>page?1:-1);}});bottom.addView(pageSeek);}
  bottom.setVisibility(barsShown?View.VISIBLE:View.GONE);pageLabel.setText(pageText(0));prefetch(1);}
 private String pageText(int i){return t("Sayfa ","Rûpel ")+(i+1)+" / "+pages;}
 private void turnPage(int d){if(pdf==null)return;int to=page+d;if(to<0||to>=pages){zoom.animate().translationX(-d*dp(18)).setDuration(90).withEndAction(new Runnable(){public void run(){zoom.animate().translationX(0).setDuration(140);}});return;}goPage(to,d);}
 private void goPage(final int to,final int dir){if(to==page||pdf==null)return;page=to;pageLabel.setText(pageText(to));if(pageSeek!=null)pageSeek.setProgress(to);final int token=++pageToken;
  Bitmap ready=rendered.get(to);if(ready!=null){zoom.show(ready,dir);prefetch(to+dir);return;}
  worker.execute(new Runnable(){public void run(){try{final Bitmap b=pageBitmap(to);runOnUiThread(new Runnable(){public void run(){if(token==pageToken){zoom.show(b,dir);prefetch(to+dir);}}});}catch(Exception ignored){}}});}
 /** The page after the one shown is drawn ahead, so turning to it is instant. */
 private void prefetch(final int i){if(pdf==null||i<0||i>=pages||rendered.get(i)!=null)return;worker.execute(new Runnable(){public void run(){try{pageBitmap(i);}catch(Exception ignored){}}});}

 // ---------------------------------------------------------------- text
 private void showText(String s){stage.removeAllViews();ScrollView sc=new ScrollView(this);TextView tv=ui.label(s.length()>400000?s.substring(0,400000)+"\n…":s,15,0xFFE8E6F0,false);
  if(Arrays.asList("csv","tsv","json","xml","log","srt","vtt").contains(ext))tv.setTypeface(Typeface.MONOSPACE);tv.setTextIsSelectable(true);
  tv.setPadding(dp(20),dp(90),dp(20),dp(40));sc.addView(tv);sc.setBackgroundColor(0xFF131218);stage.addView(sc,new FrameLayout.LayoutParams(-1,-1));
  subtitle.setText(describe(s.split("\n",-1).length+t(" satır"," rêz")));}

 // ---------------------------------------------------------------- video and sound
 private void showVideo(){stage.removeAllViews();video=new VideoView(this);final VideoView v=video;stage.addView(v,new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER));
  View catcher=new View(this);catcher.setOnClickListener(new View.OnClickListener(){public void onClick(View x){toggleBars();}});stage.addView(catcher,new FrameLayout.LayoutParams(-1,-1));
  controls();
  v.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer mp){seek.setMax(Math.max(1,v.getDuration()));subtitle.setText(describe(mp.getVideoWidth()+" × "+mp.getVideoHeight()+" · "+MainActivity.clock(v.getDuration()/1000.0)));v.start();tick();
   handler.postDelayed(new Runnable(){public void run(){if(v.isPlaying()&&barsShown)toggleBars();}},2500);}});
  v.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer mp){icon();if(!barsShown)toggleBars();}});
  v.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer mp,int a,int b){release();message(t("Bu video telefonun oynatıcısıyla gösterilemiyor.\nDönüştürücüde MP4'e çevirebilirsin.","Ev vîdyo bi lîstikvana telefonê nayê nîşandan.\nDi Veguherînerê de dikarî bikî MP4."),false);bottom.setVisibility(View.GONE);return true;}});
  v.setVideoURI(uri);}
 private void showSound(){stage.removeAllViews();LinearLayout c=ui.column();c.setGravity(Gravity.CENTER);c.addView(ui.badge("audio",120,0xFF24222C,ui.accent));c.addView(ui.space(18));
  TextView n=ui.label(name,17,0xFFFFFFFF,true);n.setGravity(Gravity.CENTER);n.setPadding(dp(32),0,dp(32),0);c.addView(n);stage.addView(c,new FrameLayout.LayoutParams(-1,-1));
  controls();sound=new MediaPlayer();final MediaPlayer mp=sound;
  try{mp.setDataSource(this,uri);mp.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer x){seek.setMax(Math.max(1,x.getDuration()));subtitle.setText(describe(MainActivity.clock(x.getDuration()/1000.0)));x.start();tick();}});
   mp.setOnCompletionListener(new MediaPlayer.OnCompletionListener(){public void onCompletion(MediaPlayer x){icon();}});
   mp.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer x,int a,int b){release();message(t("Bu ses telefonda çalınamıyor.\nDönüştürücüde MP3'e çevirebilirsin.","Ev deng li telefonê nayê lêdan.\nDi Veguherînerê de dikarî bikî MP3."),false);bottom.setVisibility(View.GONE);return true;}});
   mp.prepareAsync();}catch(Exception e){release();message(t("Bu ses telefonda çalınamıyor.","Ev deng li telefonê nayê lêdan."),false);}}
 private boolean playing(){try{return video!=null?video.isPlaying():sound!=null&&sound.isPlaying();}catch(Exception e){return false;}}
 private int position(){try{return video!=null?video.getCurrentPosition():sound!=null?sound.getCurrentPosition():0;}catch(Exception e){return 0;}}
 private int duration(){try{return video!=null?video.getDuration():sound!=null?sound.getDuration():0;}catch(Exception e){return 0;}}
 private void seekTo(int ms){try{if(video!=null)video.seekTo(ms);else if(sound!=null)sound.seekTo(ms);}catch(Exception ignored){}}
 private void controls(){bottom.removeAllViews();LinearLayout r=ui.row();playButton=iconButton("pause",new View.OnClickListener(){public void onClick(View v){
   try{if(playing()){if(video!=null)video.pause();else sound.pause();}else{if(video!=null)video.start();else if(sound!=null)sound.start();tick();}}catch(Exception ignored){}icon();}});
  seek=new SeekBar(this);tint(seek);timeLabel=ui.label("0:00 / 0:00",13,0xFFFFFFFF,false);r.addView(playButton);r.addView(seek,new LinearLayout.LayoutParams(0,-2,1));r.addView(timeLabel);bottom.addView(r);
  seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int v,boolean user){if(user){seekTo(v);time(v);}}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});
  bottom.setVisibility(barsShown?View.VISIBLE:View.GONE);}
 private void time(int pos){timeLabel.setText(MainActivity.tclock(pos/1000.0)+" / "+MainActivity.clock(duration()/1000.0));}
 private void icon(){if(playButton!=null)playButton.setCompoundDrawablesRelative(ui.icon(playing()?"pause":"play",0xFFFFFFFF,26),null,null,null);}
 private final Runnable ticker=new Runnable(){public void run(){if(seek==null)return;int p=position();seek.setProgress(p);time(p);icon();if(playing())handler.postDelayed(this,200);}};
 private void tick(){handler.removeCallbacks(ticker);handler.post(ticker);}
 private void tint(SeekBar s){s.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent));s.setThumbTintList(android.content.res.ColorStateList.valueOf(ui.accent));}

 // ---------------------------------------------------------------- bars and actions
 private void toggleBars(){barsShown=!barsShown;fadeBar(top,barsShown);if(bottom.getChildCount()>0)fadeBar(bottom,barsShown);
  View d=getWindow().getDecorView();d.setSystemUiVisibility(barsShown?0:View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY|View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_LAYOUT_STABLE);}
 private void fadeBar(final View v,final boolean show){v.animate().cancel();if(show){v.setVisibility(View.VISIBLE);v.setAlpha(0f);v.animate().alpha(1f).setDuration(180).start();}
  else v.animate().alpha(0f).setDuration(180).withEndAction(new Runnable(){public void run(){v.setVisibility(View.GONE);v.setAlpha(1f);}}).start();}
 private void toWorkspace(){try{Intent i=new Intent(this,MainActivity.class);i.setAction(Intent.ACTION_VIEW);i.setDataAndType(uri,mime.isEmpty()?"*/*":mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(i);finish();}
  catch(Exception e){Toast.makeText(this,t("Açılamadı.","Venebû."),Toast.LENGTH_SHORT).show();}}
 private void share(){try{Intent i=new Intent(Intent.ACTION_SEND);i.setType(mime.isEmpty()?"*/*":mime);i.putExtra(Intent.EXTRA_STREAM,uri);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,t("Paylaş","Parve bike")));}
  catch(Exception e){Toast.makeText(this,t("Paylaşılamadı.","Nehat parvekirin."),Toast.LENGTH_SHORT).show();}}
 /** Another viewer or editor; this app's own entries are left out of the list. */
 private void openElsewhere(){try{Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,mime.isEmpty()?"*/*":mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
   Intent c=Intent.createChooser(i,t("Başka uygulamayla aç","Bi sepaneke din veke"));c.putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS,new ComponentName[]{new ComponentName(this,QuickView.class),new ComponentName(this,MainActivity.class)});startActivity(c);}
  catch(Exception e){Toast.makeText(this,t("Bu dosyayı açabilecek başka uygulama yok.","Sepaneke din tune ku vê dosyeyê veke."),Toast.LENGTH_SHORT).show();}}
 static void deleteTree(File f){if(f==null||!f.exists())return;File[] k=f.listFiles();if(k!=null)for(File x:k)deleteTree(x);f.delete();}
}
