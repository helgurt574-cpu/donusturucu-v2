package org.local.donusturucu;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.*;
import android.view.*;
import java.util.*;

/** Custom views of the new screen. */
final class Widgets {
 private Widgets(){}

 /** Ring of output formats; tap a slice to choose it, tap the centre to turn to the other side. */
 static final class Donut extends View {
  interface Listener {void chosen(String format);void flipped(boolean back);}
  final Ui ui;String[] front=new String[0],back=new String[0];String selected="",title="",hint="";boolean showBack;Listener listener;
  private int pressed=-1;private float appear=1f;
  private final Paint fill=new Paint(Paint.ANTI_ALIAS_FLAG),line=new Paint(Paint.ANTI_ALIAS_FLAG),label=new Paint(Paint.ANTI_ALIAS_FLAG),shadow=new Paint(Paint.ANTI_ALIAS_FLAG);
  Donut(Context c,Ui ui){super(c);this.ui=ui;line.setStyle(Paint.Style.STROKE);label.setTextAlign(Paint.Align.CENTER);label.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
   shadow.setColor(ui.surface);shadow.setShadowLayer(ui.dp(14),0,ui.dp(4),ui.dark?0x66000000:0x26302650);setContentDescription("format");}
  String[] items(){return showBack&&back.length>0?back:front;}
  void set(String[] front,String[] back,String selected,String title,String hint){this.front=front;this.back=back;this.selected=selected;this.title=title;this.hint=hint;
   if(showBack&&Arrays.asList(front).contains(selected))showBack=false;if(!showBack&&back.length>0&&Arrays.asList(back).contains(selected)&&!Arrays.asList(front).contains(selected))showBack=true;invalidate();}
  @Override protected void onMeasure(int w,int h){int size=MeasureSpec.getSize(w);size=Math.min(size,ui.dp(340));setMeasuredDimension(MeasureSpec.getSize(w),size);}
  private float cx(){return getWidth()/2f;}private float cy(){return getHeight()/2f;}private float outer(){return Math.min(getWidth(),getHeight())/2f-ui.dp(14);}private float inner(){return outer()*0.47f;}
  @Override protected void onDraw(Canvas c){
   String[] it=items();float cx=cx(),cy=cy(),R=outer(),r=inner();c.save();c.scale(0.94f+0.06f*appear,0.94f+0.06f*appear,cx,cy);
   c.drawCircle(cx,cy,R+ui.dp(4),shadow);
   int n=Math.max(1,it.length);float gap=it.length>1?2.2f:0,step=360f/n;RectF o=new RectF(cx-R,cy-R,cx+R,cy+R),in=new RectF(cx-r,cy-r,cx+r,cy+r);
   for(int i=0;i<it.length;i++){float start=-90-step/2+i*step+gap/2,sweep=step-gap;Path p=new Path();p.arcTo(o,start,sweep);p.arcTo(in,start+sweep,-sweep);p.close();
    boolean sel=it[i].equals(selected);fill.setColor(sel?ui.accent:i==pressed?ui.blend(ui.segment,ui.accent,0.18f):ui.segment);fill.setAlpha((int)(255*appear));c.drawPath(p,fill);
    line.setColor(ui.surface);line.setStrokeWidth(ui.dp(3));c.drawPath(p,line);
    double mid=Math.toRadians(-90+i*step);float lr=(R+r)/2f;float tx=cx+(float)Math.cos(mid)*lr,ty=cy+(float)Math.sin(mid)*lr;
    String[] parts=it[i].split("\n");label.setColor(sel?ui.onAccent:ui.text);label.setTextSize(ui.dp(n>9?12.5f:14.5f));label.setFakeBoldText(true);
    if(parts.length==1)c.drawText(parts[0],tx,ty+label.getTextSize()*0.36f,label);
    else{c.drawText(parts[0],tx,ty,label);label.setFakeBoldText(false);label.setTextSize(ui.dp(11));label.setColor(sel?0xDDFFFFFF:ui.muted);c.drawText(parts[1],tx,ty+ui.dp(14),label);}}
   fill.setColor(ui.border);c.drawCircle(cx,cy,r-ui.dp(4),fill);fill.setColor(ui.surface);c.drawCircle(cx,cy,r-ui.dp(9),fill);
   label.setFakeBoldText(true);label.setColor(ui.text);label.setTextSize(ui.dp(17));c.drawText(title,cx,cy+ui.dp(2),label);
   label.setFakeBoldText(false);label.setColor(ui.muted);label.setTextSize(ui.dp(11.5f));c.drawText(hint,cx,cy+ui.dp(19),label);
   c.restore();}
  private int hit(float x,float y){float dx=x-cx(),dy=y-cy();double d=Math.sqrt(dx*dx+dy*dy);if(d<inner()-ui.dp(6))return -2;if(d>outer()+ui.dp(6))return -1;
   String[] it=items();if(it.length==0)return -1;double a=Math.toDegrees(Math.atan2(dy,dx))+90;float step=360f/it.length;a=(a+step/2+720)%360;return (int)(a/step)%it.length;}
  @Override public boolean onTouchEvent(MotionEvent e){int h=hit(e.getX(),e.getY());
   switch(e.getActionMasked()){
    case MotionEvent.ACTION_DOWN:pressed=h>=0?h:-1;invalidate();return true;
    case MotionEvent.ACTION_MOVE:if(pressed!=(h>=0?h:-1)){pressed=h>=0?h:-1;invalidate();}return true;
    case MotionEvent.ACTION_UP:pressed=-1;
     if(h>=0){selected=items()[h];performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);if(listener!=null)listener.chosen(selected);}
     else if(h==-2&&back.length>0){flip();}
     invalidate();return true;
    case MotionEvent.ACTION_CANCEL:pressed=-1;invalidate();return true;}
   return super.onTouchEvent(e);}
  void flip(){showBack=!showBack;animateIn();if(listener!=null)listener.flipped(showBack);}
  void animateIn(){ValueAnimator a=ValueAnimator.ofFloat(0f,1f);a.setDuration(260);a.addUpdateListener(new ValueAnimator.AnimatorUpdateListener(){public void onAnimationUpdate(ValueAnimator v){appear=(Float)v.getAnimatedValue();invalidate();}});a.start();}
 }

 /** Picture viewer: plain, selecting areas (watermark) or before/after comparison with a slider. */
 static final class Picture extends View {
  interface Listener {void changed(List<double[]> regions);}
  static final int VIEW=0,SELECT=1,COMPARE=2;
  final Ui ui;Bitmap before,after;int mode=VIEW;final List<double[]> regions=new ArrayList<double[]>();int active=-1;float split=0.5f;Listener listener;String beforeLabel="",afterLabel="";
  private final Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG|Paint.ANTI_ALIAS_FLAG),stroke=new Paint(Paint.ANTI_ALIAS_FLAG),shade=new Paint(Paint.ANTI_ALIAS_FLAG),tag=new Paint(Paint.ANTI_ALIAS_FLAG);
  private float downX,downY;private int drag=0;private double[] start;private final RectF frame=new RectF();private final Path clip=new Path();
  Picture(Context c,Ui ui){super(c);this.ui=ui;stroke.setStyle(Paint.Style.STROKE);tag.setTextSize(ui.dp(12));tag.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));}
  void show(Bitmap b){before=b;after=null;requestLayout();invalidate();}
  private Bitmap fadeFrom;private float fade=1f;
  /** Next page or another frame: the new picture fades in over the current one. */
  void crossfade(Bitmap b){if(before==null||b==null){show(b);return;}fadeFrom=before;before=b;fade=0f;requestLayout();
   ValueAnimator a=ValueAnimator.ofFloat(0f,1f);a.setDuration(220);a.addUpdateListener(new ValueAnimator.AnimatorUpdateListener(){public void onAnimationUpdate(ValueAnimator v){fade=(Float)v.getAnimatedValue();if(fade>=1f)fadeFrom=null;invalidate();}});a.start();}
  void compare(Bitmap a,Bitmap b,String la,String lb){before=a;after=b;beforeLabel=la;afterLabel=lb;mode=COMPARE;requestLayout();invalidate();}
  @Override protected void onMeasure(int w,int h){int width=MeasureSpec.getSize(w);int height=ui.dp(220);
   if(before!=null){height=(int)((float)width*before.getHeight()/Math.max(1,before.getWidth()));height=Math.max(ui.dp(140),Math.min(height,ui.dp(mode==VIEW?360:440)));}
   setMeasuredDimension(width,height);}
  private void layoutFrame(){if(before==null){frame.set(0,0,getWidth(),getHeight());return;}float s=Math.min((float)getWidth()/before.getWidth(),(float)getHeight()/before.getHeight());float w=before.getWidth()*s,h=before.getHeight()*s;frame.set((getWidth()-w)/2,(getHeight()-h)/2,(getWidth()+w)/2,(getHeight()+h)/2);}
  @Override protected void onDraw(Canvas c){
   layoutFrame();clip.reset();clip.addRoundRect(new RectF(0,0,getWidth(),getHeight()),ui.dp(14),ui.dp(14),Path.Direction.CW);c.save();c.clipPath(clip);c.drawColor(ui.dark?0xFF0E0D12:0xFFE9E7EF);
   if(before!=null&&!before.isRecycled()){
    if(mode==COMPARE&&after!=null&&!after.isRecycled()){float x=frame.left+frame.width()*split;
     c.save();c.clipRect(frame.left,frame.top,x,frame.bottom);c.drawBitmap(before,null,frame,paint);c.restore();
     c.save();c.clipRect(x,frame.top,frame.right,frame.bottom);c.drawBitmap(after,null,frame,paint);c.restore();
     stroke.setColor(0xFFFFFFFF);stroke.setStrokeWidth(ui.dp(2.5f));c.drawLine(x,frame.top,x,frame.bottom,stroke);
     shade.setColor(0xFFFFFFFF);c.drawCircle(x,getHeight()/2f,ui.dp(15),shade);shade.setColor(ui.accent);c.drawCircle(x,getHeight()/2f,ui.dp(11),shade);
     tag.setColor(0xFFFFFFFF);tag.setTextAlign(Paint.Align.CENTER);c.drawText("‹ ›",x,getHeight()/2f+ui.dp(4),tag);
     pill(c,beforeLabel,frame.left+ui.dp(10),frame.bottom-ui.dp(34),false);pill(c,afterLabel,frame.right-ui.dp(10),frame.bottom-ui.dp(34),true);}
    else if(fadeFrom!=null&&!fadeFrom.isRecycled()&&fade<1f){c.drawBitmap(fadeFrom,null,frame,paint);paint.setAlpha((int)(255*fade));c.drawBitmap(before,null,frame,paint);paint.setAlpha(255);}
    else c.drawBitmap(before,null,frame,paint);}
   if(mode==SELECT){
    shade.setColor(0x55000000);if(!regions.isEmpty()){Path dim=new Path();dim.setFillType(Path.FillType.EVEN_ODD);dim.addRect(frame,Path.Direction.CW);for(double[] r:regions)dim.addRect(toView(r),Path.Direction.CW);c.drawPath(dim,shade);}
    for(int i=0;i<regions.size();i++){RectF v=toView(regions.get(i));boolean on=i==active;stroke.setColor(on?ui.accent:0xFFFFFFFF);stroke.setStrokeWidth(ui.dp(on?2.5f:1.5f));c.drawRoundRect(v,ui.dp(4),ui.dp(4),stroke);
     if(on){shade.setColor(0xFFFFFFFF);for(float[] k:new float[][]{{v.left,v.top},{v.right,v.top},{v.left,v.bottom},{v.right,v.bottom}}){c.drawCircle(k[0],k[1],ui.dp(8),shade);}shade.setColor(ui.accent);for(float[] k:new float[][]{{v.left,v.top},{v.right,v.top},{v.left,v.bottom},{v.right,v.bottom}})c.drawCircle(k[0],k[1],ui.dp(5),shade);}}}
   c.restore();}
  private void pill(Canvas c,String s,float x,float y,boolean right){if(s==null||s.length()==0)return;float w=tag.measureText(s)+ui.dp(16),h=ui.dp(24);RectF r=right?new RectF(x-w,y,x,y+h):new RectF(x,y,x+w,y+h);shade.setColor(0xAA000000);c.drawRoundRect(r,h/2,h/2,shade);tag.setColor(0xFFFFFFFF);tag.setTextAlign(Paint.Align.CENTER);c.drawText(s,r.centerX(),r.centerY()+ui.dp(4),tag);}
  private RectF toView(double[] r){return new RectF((float)(frame.left+r[0]*frame.width()),(float)(frame.top+r[1]*frame.height()),(float)(frame.left+(r[0]+r[2])*frame.width()),(float)(frame.top+(r[1]+r[3])*frame.height()));}
  private double nx(float x){return Math.max(0,Math.min(1,(x-frame.left)/Math.max(1,frame.width())));}private double ny(float y){return Math.max(0,Math.min(1,(y-frame.top)/Math.max(1,frame.height())));}
  @Override public boolean onTouchEvent(MotionEvent e){
   if(mode==VIEW||before==null)return super.onTouchEvent(e);layoutFrame();float x=e.getX(),y=e.getY();
   if(mode==COMPARE){if(e.getActionMasked()==MotionEvent.ACTION_DOWN)getParent().requestDisallowInterceptTouchEvent(true);split=(float)nx(x);invalidate();return true;}
   switch(e.getActionMasked()){
    case MotionEvent.ACTION_DOWN:{getParent().requestDisallowInterceptTouchEvent(true);downX=x;downY=y;drag=0;
     float near=ui.dp(26);
     for(int i=regions.size()-1;i>=0&&drag==0;i--){RectF v=toView(regions.get(i));
      if(Math.hypot(x-v.left,y-v.top)<near)drag=1;else if(Math.hypot(x-v.right,y-v.top)<near)drag=2;else if(Math.hypot(x-v.left,y-v.bottom)<near)drag=3;else if(Math.hypot(x-v.right,y-v.bottom)<near)drag=4;else if(v.contains(x,y))drag=5;
      if(drag!=0){active=i;start=regions.get(i).clone();}}
     if(drag==0){if(regions.size()>=4)regions.remove(0);double[] r={nx(x),ny(y),0,0};regions.add(r);active=regions.size()-1;start=r.clone();drag=6;}
     invalidate();return true;}
    case MotionEvent.ACTION_MOVE:{if(active<0)return true;double[] r=regions.get(active);double dx=nx(x)-nx(downX),dy=ny(y)-ny(downY);
     double l=start[0],t=start[1],rr=start[0]+start[2],b=start[1]+start[3];
     if(drag==5){l=Math.max(0,Math.min(1-start[2],l+dx));t=Math.max(0,Math.min(1-start[3],t+dy));rr=l+start[2];b=t+start[3];}
     else if(drag==6){l=Math.min(start[0],nx(x));t=Math.min(start[1],ny(y));rr=Math.max(start[0],nx(x));b=Math.max(start[1],ny(y));}
     else{if(drag==1||drag==3)l=Math.min(rr-0.01,nx(x));if(drag==2||drag==4)rr=Math.max(l+0.01,nx(x));if(drag==1||drag==2)t=Math.min(b-0.01,ny(y));if(drag==3||drag==4)b=Math.max(t+0.01,ny(y));}
     r[0]=l;r[1]=t;r[2]=rr-l;r[3]=b-t;invalidate();return true;}
    case MotionEvent.ACTION_UP:case MotionEvent.ACTION_CANCEL:{
     if(active>=0&&active<regions.size()){double[] r=regions.get(active);if(r[2]<0.015||r[3]<0.015){if(drag==6){regions.remove(active);active=regions.size()-1;}}}
     drag=0;invalidate();if(listener!=null)listener.changed(regions);return true;}}
   return super.onTouchEvent(e);}
 }

 /** Loudness bars of a sound; the played part is coloured. Tap to jump. */
 static final class Wave extends View {
  interface Seek {void to(float fraction);}
  final Ui ui;float[] peaks=new float[0];float played=0;Seek seek;final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
  Wave(Context c,Ui ui){super(c);this.ui=ui;}
  @Override protected void onMeasure(int w,int h){setMeasuredDimension(MeasureSpec.getSize(w),ui.dp(64));}
  @Override protected void onDraw(Canvas c){int n=peaks.length;if(n==0){p.setColor(ui.border);c.drawRoundRect(new RectF(0,getHeight()/2f-ui.dp(1),getWidth(),getHeight()/2f+ui.dp(1)),4,4,p);return;}
   float bar=(float)getWidth()/n,w=Math.max(ui.dp(1.5f),bar*0.62f),mid=getHeight()/2f;
   for(int i=0;i<n;i++){float h=Math.max(ui.dp(2),peaks[i]*(getHeight()-ui.dp(6)));p.setColor((i+0.5f)/n<=played?ui.accent:ui.blend(ui.muted,ui.surface,0.45f));float x=i*bar+(bar-w)/2;c.drawRoundRect(new RectF(x,mid-h/2,x+w,mid+h/2),w/2,w/2,p);}}
  @Override public boolean onTouchEvent(MotionEvent e){if(e.getActionMasked()==MotionEvent.ACTION_DOWN)getParent().requestDisallowInterceptTouchEvent(true);
   if(e.getActionMasked()==MotionEvent.ACTION_UP&&seek!=null)seek.to(Math.max(0,Math.min(1,e.getX()/Math.max(1,getWidth()))));return true;}
 }
}
