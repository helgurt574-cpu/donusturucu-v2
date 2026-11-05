package org.local.donusturucu;
import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.*;
import android.graphics.drawable.*;
import android.text.InputType;
import android.util.TypedValue;
import android.view.*;
import android.widget.*;
import java.util.*;

/** Design system: soft surfaces, rounded cards, pill buttons, chips and line icons. */
final class Ui {
 final Context c;final boolean dark;final float density;
 int bg,surface,surface2,border,text,muted,accent,accentSoft,accentText,segment,danger,success,onAccent;
 static final int[][] ACCENTS={{0x6E5FD8,0x9A8DF2},{0x2F74D9,0x6CA4F5},{0x1E9466,0x4CC394},{0xD9573F,0xF08A73},{0xC54383,0xE57CB0}};
 Ui(Context c,boolean dark,int accentIndex){this.c=c;this.dark=dark;density=c.getResources().getDisplayMetrics().density;
  int[] a=ACCENTS[Math.max(0,Math.min(ACCENTS.length-1,accentIndex))];
  if(dark){bg=0xFF131218;surface=0xFF1C1B22;surface2=0xFF24222C;border=0xFF33303D;text=0xFFECEAF3;muted=0xFFA19EAF;segment=0xFF2A2833;accent=0xFF000000|a[1];danger=0xFFE5646E;success=0xFF4CC394;}
  else{bg=0xFFF6F5F2;surface=0xFFFFFFFF;surface2=0xFFEFEDF5;border=0xFFE4E1EB;text=0xFF1E1D24;muted=0xFF6B6878;segment=0xFFF1F0EC;accent=0xFF000000|a[0];danger=0xFFC23C47;success=0xFF1E9466;}
  accentSoft=blend(accent,dark?surface:0xFFFFFFFF,dark?0.78f:0.86f);accentText=dark?blend(accent,0xFFFFFFFF,0.35f):blend(accent,0xFF000000,0.18f);onAccent=dark?0xFF17142A:0xFFFFFFFF;}
 static int blend(int a,int b,float t){return Color.rgb((int)(Color.red(a)*(1-t)+Color.red(b)*t),(int)(Color.green(a)*(1-t)+Color.green(b)*t),(int)(Color.blue(a)*(1-t)+Color.blue(b)*t));}
 int dp(float x){return (int)(x*density+.5f);}

 GradientDrawable round(int fill,float radius,int stroke){GradientDrawable g=new GradientDrawable();g.setColor(fill);g.setCornerRadius(dp(radius));if(stroke!=0)g.setStroke(dp(1),stroke);return g;}
 Drawable ripple(Drawable content,float radius){GradientDrawable mask=round(0xFFFFFFFF,radius,0);return new RippleDrawable(ColorStateList.valueOf(dark?0x33FFFFFF:0x1F000000),content,mask);}

 TextView label(String s,float sp,int color,boolean bold){TextView v=new TextView(c);v.setText(s);v.setTextSize(TypedValue.COMPLEX_UNIT_SP,sp);v.setTextColor(color);v.setTextDirection(View.TEXT_DIRECTION_FIRST_STRONG);
  if(bold)v.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));v.setLineSpacing(0,1.12f);return v;}
 TextView title(String s){TextView v=label(s,26,text,true);v.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));return v;}
 TextView section(String s){TextView v=label(s,16,text,true);v.setPadding(0,dp(18),0,dp(8));return v;}
 TextView body(String s){return label(s,14,muted,false);}
 TextView small(String s){return label(s,12.5f,muted,false);}

 LinearLayout card(){LinearLayout v=column();v.setPadding(dp(16),dp(14),dp(16),dp(16));v.setBackground(round(surface,18,border));v.setElevation(0);return v;}
 LinearLayout column(){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.VERTICAL);return v;}
 LinearLayout row(){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.HORIZONTAL);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
 LinearLayout.LayoutParams lp(int w,int h){return new LinearLayout.LayoutParams(w,h);}
 LinearLayout.LayoutParams margins(int w,int h,int l,int t,int r,int b){LinearLayout.LayoutParams p=lp(w,h);p.setMargins(dp(l),dp(t),dp(r),dp(b));return p;}
 LinearLayout.LayoutParams weight(float w){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,-2,w);return p;}
 View space(int h){View v=new View(c);v.setLayoutParams(lp(-1,dp(h)));return v;}

 /** Pill button: primary (filled), soft (tinted) or plain (text only). */
 TextView button(String s,String icon,int style,View.OnClickListener l){
  TextView b=label(s,15,style==0?onAccent:style==1?accentText:style==3?danger:text,true);b.setGravity(Gravity.CENTER);b.setPadding(dp(18),dp(12),dp(18),dp(12));b.setMinHeight(dp(48));
  int fill=style==0?accent:style==1?accentSoft:style==3?blend(danger,surface,dark?0.75f:0.88f):0x00000000;b.setBackground(ripple(round(fill,24,style==2?border:0),24));
  if(icon!=null){Drawable d=icon(icon,b.getCurrentTextColor(),20);b.setCompoundDrawablesRelative(d,null,null,null);b.setCompoundDrawablePadding(dp(8));}
  b.setOnClickListener(l);b.setClickable(true);b.setFocusable(true);return b;}
 void enable(View v,boolean on){v.setEnabled(on);v.setAlpha(on?1f:0.45f);}

 TextView chip(String s,boolean selected,View.OnClickListener l){
  TextView v=label(s,14,selected?accentText:text,selected);v.setGravity(Gravity.CENTER);v.setPadding(dp(14),dp(8),dp(14),dp(8));v.setMinHeight(dp(38));
  v.setBackground(ripple(round(selected?accentSoft:surface,19,selected?accent:border),19));v.setOnClickListener(l);
  if(selected){Drawable d=icon("check",accentText,16);v.setCompoundDrawablesRelative(d,null,null,null);v.setCompoundDrawablePadding(dp(4));}
  return v;}
 /** Wrapping row of chips with even gaps. */
 Flow flow(){Flow f=new Flow(c,dp(8));return f;}

 EditText input(String value,String hint,boolean number){EditText e=new EditText(c);e.setText(value);e.setHint(hint);e.setSingleLine(true);e.setTextColor(text);e.setHintTextColor(muted);e.setTextSize(15);
  e.setBackground(round(surface2,12,border));e.setPadding(dp(14),dp(11),dp(14),dp(11));if(number)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);return e;}

 /** Round icon tile used in lists and the tool grid. */
 FrameLayout badge(String icon,int size,int fill,int tint){FrameLayout f=new FrameLayout(c);f.setBackground(round(fill,size*0.3f,0));ImageView i=new ImageView(c);i.setImageDrawable(icon(icon,tint,(int)(size*0.52f)));
  f.addView(i,new FrameLayout.LayoutParams(dp(size*0.52f),dp(size*0.52f),Gravity.CENTER));f.setLayoutParams(lp(dp(size),dp(size)));return f;}

 Drawable icon(String name,int color,int sizeDp){IconDrawable d=new IconDrawable(path(name),color);d.setBounds(0,0,dp(sizeDp),dp(sizeDp));return d;}

 /** Wraps children onto new lines. */
 static final class Flow extends ViewGroup{final int gap;Flow(Context c,int gap){super(c);this.gap=gap;}
  @Override protected void onMeasure(int ws,int hs){int max=MeasureSpec.getSize(ws)-getPaddingLeft()-getPaddingRight();int x=0,y=0,line=0;
   for(int i=0;i<getChildCount();i++){View v=getChildAt(i);if(v.getVisibility()==GONE)continue;measureChild(v,MeasureSpec.makeMeasureSpec(max,MeasureSpec.AT_MOST),hs);int w=v.getMeasuredWidth(),h=v.getMeasuredHeight();
    if(x>0&&x+w>max){x=0;y+=line+gap;line=0;}x+=w+gap;line=Math.max(line,h);}
   setMeasuredDimension(MeasureSpec.getSize(ws),y+line+getPaddingTop()+getPaddingBottom());}
  @Override protected void onLayout(boolean ch,int l,int t,int r,int b){int max=r-l-getPaddingLeft()-getPaddingRight();int x=0,y=0,line=0;boolean rtl=getLayoutDirection()==LAYOUT_DIRECTION_RTL;
   for(int i=0;i<getChildCount();i++){View v=getChildAt(i);if(v.getVisibility()==GONE)continue;int w=v.getMeasuredWidth(),h=v.getMeasuredHeight();if(x>0&&x+w>max){x=0;y+=line+gap;line=0;}
    int left=rtl?getPaddingLeft()+max-x-w:getPaddingLeft()+x;v.layout(left,getPaddingTop()+y,left+w,getPaddingTop()+y+h);x+=w+gap;line=Math.max(line,h);}}
 }

 static final class IconDrawable extends Drawable{final Path p;final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);IconDrawable(Path p,int color){this.p=p;paint.setColor(color);}
  @Override public void draw(Canvas c){Rect b=getBounds();c.save();c.translate(b.left,b.top);c.scale(b.width()/24f,b.height()/24f);c.drawPath(p,paint);c.restore();}
  @Override public void setAlpha(int a){paint.setAlpha(a);}@Override public void setColorFilter(ColorFilter f){paint.setColorFilter(f);}@Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
  @Override public int getIntrinsicWidth(){return getBounds().width();}@Override public int getIntrinsicHeight(){return getBounds().height();}}

 // Material icons (Apache License 2.0), 24×24 path data.
 static final Map<String,String> ICONS=new HashMap<String,String>();
 static{
  ICONS.put("home","M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z");
  ICONS.put("history","M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z");
  ICONS.put("tune","M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z");
  ICONS.put("upload","M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z");
  ICONS.put("folder","M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z");
  ICONS.put("play","M8 5v14l11-7z");ICONS.put("pause","M6 19h4V5H6v14zm8-14v14h4V5h-4z");ICONS.put("stop","M6 6h12v12H6z");
  ICONS.put("close","M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z");
  ICONS.put("back","M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z");
  ICONS.put("check","M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z");
  ICONS.put("cut","M9.64 7.64c.23-.5.36-1.05.36-1.64 0-2.21-1.79-4-4-4S2 3.79 2 6s1.79 4 4 4c.59 0 1.14-.13 1.64-.36L10 12l-2.36 2.36C7.14 14.13 6.59 14 6 14c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4c0-.59-.13-1.14-.36-1.64L12 14l7 7h3v-1L9.64 7.64zM6 8c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm0 12c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm6-7.5c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zM19 3l-6 6 2 2 7-7V3z");
  ICONS.put("video","M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z");
  ICONS.put("audio","M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z");
  ICONS.put("image","M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z");
  ICONS.put("doc","M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z");
  ICONS.put("wand","M7.5 5.6L10 7 8.6 4.5 10 2 7.5 3.4 5 2l1.4 2.5L5 7zm12 9.8L17 14l1.4 2.5L17 19l2.5-1.4L22 19l-1.4-2.5L22 14zM22 2l-2.5 1.4L17 2l1.4 2.5L17 7l2.5-1.4L22 7l-1.4-2.5zm-7.63 5.29c-.39-.39-1.02-.39-1.41 0L1.29 18.96c-.39.39-.39 1.02 0 1.41l2.34 2.34c.39.39 1.02.39 1.41 0L16.7 11.05c.39-.39.39-1.02 0-1.41l-2.33-2.35zm-1.03 5.49l-2.12-2.12 2.44-2.44 2.12 2.12-2.44 2.44z");
  ICONS.put("wave","M7 18h2V6H7v12zm4 4h2V2h-2v20zm-8-8h2v-4H3v4zm12 4h2V6h-2v12zm4-8v4h2v-4h-2z");
  ICONS.put("rotate","M15.55 5.55L11 1v3.07C7.06 4.56 4 7.92 4 12s3.05 7.44 7 7.93v-2.02c-2.84-.48-5-2.94-5-5.91s2.16-5.43 5-5.91V10l4.55-4.45zM19.93 11c-.17-1.39-.72-2.73-1.62-3.89l-1.42 1.42c.54.75.88 1.6 1.02 2.47h2.02zM13 17.9v2.02c1.39-.17 2.74-.71 3.9-1.61l-1.44-1.44c-.75.54-1.59.89-2.46 1.03zm3.89-2.42l1.42 1.41c.9-1.16 1.45-2.5 1.62-3.89h-2.02c-.14.87-.48 1.72-1.02 2.48z");
  ICONS.put("speed","M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z");
  ICONS.put("mute","M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z");
  ICONS.put("volume","M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z");
  ICONS.put("camera","M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z");
  ICONS.put("subtitles","M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 12h4v2H4v-2zm10 6H4v-2h10v2zm6 0h-4v-2h4v2zm0-4H10v-2h10v2z");
  ICONS.put("mic","M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z");
  ICONS.put("merge","M17 20.41L18.41 19 15 15.59 13.59 17 17 20.41zM7.5 8H11v5.59L5.59 19 7 20.41l6-6V8h3.5L12 3.5 7.5 8z");
  ICONS.put("split","M14 4l2.29 2.29-2.88 2.88 1.42 1.42 2.88-2.88L20 10V4zm-4 0H4v6l2.29-2.29 4.71 4.7V20h2v-8.41l-5.29-5.3z");
  ICONS.put("delete","M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z");
  ICONS.put("text","M2.5 4v3h5v12h3V7h5V4h-13zm19 5h-9v3h3v7h3v-7h3V9z");
  ICONS.put("gif","M11.5 9H13v6h-1.5zM9 9H6c-.6 0-1 .5-1 1v4c0 .5.4 1 1 1h3c.6 0 1-.5 1-1v-2H8.5v1.5h-2v-3H10V10c0-.5-.4-1-1-1zm10 1.5V9h-4.5v6H16v-2h2v-1.5h-2v-1z");
  ICONS.put("add","M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z");
  ICONS.put("share","M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z");
  ICONS.put("open","M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z");
  ICONS.put("compress","M8 19h3v3h2v-3h3l-4-4-4 4zm8-15h-3V1h-2v3H8l4 4 4-4zM4 9v2h16V9H4zm0 3h16v2H4z");
  ICONS.put("crop","M17 15h2V7c0-1.1-.9-2-2-2H9v2h8v8zM7 17V1H5v4H1v2h4v10c0 1.1.9 2 2 2h10v4h2v-4h4v-2H7z");
  ICONS.put("info","M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z");
  ICONS.put("pages","M11.99 18.54l-7.37-5.73L3 14.07l9 7 9-7-1.63-1.27-7.38 5.74zM12 16l7.36-5.73L21 9l-9-7-9 7 1.63 1.27L12 16z");
  ICONS.put("contrast","M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93s3.06-7.44 7-7.93v15.86z");
  ICONS.put("compare","M10 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h5v2h2V1h-2v2zm0 15H5l5-6v6zm9-15h-5v2h5v13l-5-6v9h5c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z");
  ICONS.put("eye","M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z");
  ICONS.put("chevron","M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z");
  ICONS.put("chevron_left","M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z");
  ICONS.put("palette","M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z");
  ICONS.put("translate","M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z");
  ICONS.put("lock","M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z");
 }
 private static final Map<String,Path> CACHE=new HashMap<String,Path>();
 static synchronized Path path(String name){Path p=CACHE.get(name);if(p==null){String d=ICONS.get(name);p=d==null?new Path():parse(d);CACHE.put(name,p);}return p;}

 /** Small SVG path reader: M L H V C S Q T A Z, absolute and relative. */
 static Path parse(String d){
  List<Object> tokens=new ArrayList<Object>();int i=0,n=d.length();
  while(i<n){char ch=d.charAt(i);
   if(Character.isLetter(ch)&&ch!='e'&&ch!='E'){tokens.add(ch);i++;}
   else if(ch=='-'||ch=='.'||Character.isDigit(ch)){int s=i;boolean dot=ch=='.';i++;
    while(i<n){char x=d.charAt(i);if(Character.isDigit(x)){i++;}else if(x=='.'&&!dot){dot=true;i++;}else if((x=='e'||x=='E')){i++;if(i<n&&(d.charAt(i)=='-'||d.charAt(i)=='+'))i++;}else break;}
    tokens.add(Float.parseFloat(d.substring(s,i)));}
   else i++;}
  Path p=new Path();float x=0,y=0,sx=0,sy=0,cx=0,cy=0;char cmd=' ',last=' ';int k=0;
  while(k<tokens.size()){Object t=tokens.get(k);if(t instanceof Character){cmd=(Character)t;k++;if(cmd=='z'||cmd=='Z'){p.close();x=sx;y=sy;last=cmd;continue;}}
   boolean rel=Character.isLowerCase(cmd);char C=Character.toUpperCase(cmd);float ox=rel?x:0,oy=rel?y:0;
   switch(C){
    case 'M':{float a=f(tokens,k++),b=f(tokens,k++);x=ox+a;y=oy+b;p.moveTo(x,y);sx=x;sy=y;cmd=rel?'l':'L';break;}
    case 'L':{x=ox+f(tokens,k++);y=oy+f(tokens,k++);p.lineTo(x,y);break;}
    case 'H':{x=(rel?x:0)+f(tokens,k++);p.lineTo(x,y);break;}
    case 'V':{y=(rel?y:0)+f(tokens,k++);p.lineTo(x,y);break;}
    case 'C':{float x1=ox+f(tokens,k++),y1=oy+f(tokens,k++),x2=ox+f(tokens,k++),y2=oy+f(tokens,k++);x=ox+f(tokens,k++);y=oy+f(tokens,k++);p.cubicTo(x1,y1,x2,y2,x,y);cx=x2;cy=y2;break;}
    case 'S':{float x1=(last=='C'||last=='S'||last=='c'||last=='s')?2*x-cx:x,y1=(last=='C'||last=='S'||last=='c'||last=='s')?2*y-cy:y;float x2=ox+f(tokens,k++),y2=oy+f(tokens,k++);x=ox+f(tokens,k++);y=oy+f(tokens,k++);p.cubicTo(x1,y1,x2,y2,x,y);cx=x2;cy=y2;break;}
    case 'Q':{float x1=ox+f(tokens,k++),y1=oy+f(tokens,k++);x=ox+f(tokens,k++);y=oy+f(tokens,k++);p.quadTo(x1,y1,x,y);cx=x1;cy=y1;break;}
    case 'T':{float x1=(last=='Q'||last=='T'||last=='q'||last=='t')?2*x-cx:x,y1=(last=='Q'||last=='T'||last=='q'||last=='t')?2*y-cy:y;x=ox+f(tokens,k++);y=oy+f(tokens,k++);p.quadTo(x1,y1,x,y);cx=x1;cy=y1;break;}
    case 'A':{float rx=f(tokens,k++),ry=f(tokens,k++);k++;float large=f(tokens,k++),sweep=f(tokens,k++);float ex=ox+f(tokens,k++),ey=oy+f(tokens,k++);arc(p,x,y,ex,ey,rx,ry,large!=0,sweep!=0);x=ex;y=ey;break;}
    default:k++;}
   last=cmd;}
  return p;}
 private static float f(List<Object> t,int k){Object o=t.get(k);return o instanceof Float?(Float)o:0;}
 /** Endpoint arc to Path.arcTo (no axis rotation, which these icons do not use). */
 private static void arc(Path p,float x1,float y1,float x2,float y2,float rx,float ry,boolean large,boolean sweep){
  if(rx==0||ry==0){p.lineTo(x2,y2);return;}rx=Math.abs(rx);ry=Math.abs(ry);
  double dx=(x1-x2)/2.0,dy=(y1-y2)/2.0;double l=dx*dx/(rx*rx)+dy*dy/(ry*ry);if(l>1){rx*=Math.sqrt(l);ry*=Math.sqrt(l);}
  double num=rx*rx*ry*ry-rx*rx*dy*dy-ry*ry*dx*dx,den=rx*rx*dy*dy+ry*ry*dx*dx;double co=Math.sqrt(Math.max(0,num/den))*(large==sweep?-1:1);
  double cxp=co*rx*dy/ry,cyp=-co*ry*dx/rx;double cx=cxp+(x1+x2)/2.0,cy=cyp+(y1+y2)/2.0;
  double a1=Math.atan2((dy-cyp)/ry,(dx-cxp)/rx),a2=Math.atan2((-dy-cyp)/ry,(-dx-cxp)/rx);double da=a2-a1;
  if(sweep&&da<0)da+=2*Math.PI;else if(!sweep&&da>0)da-=2*Math.PI;
  p.arcTo(new RectF((float)(cx-rx),(float)(cy-ry),(float)(cx+rx),(float)(cy+ry)),(float)Math.toDegrees(a1),(float)Math.toDegrees(da),false);}
}
