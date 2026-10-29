package org.local.donusturucu;
import android.content.Context;
import android.app.ActivityManager;
import com.k2fsa.sherpa.onnx.*;
import java.io.*;import java.util.*;
/** Bundled multilingual Whisper small int8; bounded PCM chunks, no remote calls. */
final class SpeechEngine {
 interface Host {void check()throws Exception;void run(List<String> args)throws Exception;void progress(double current,double total);}
 private final Context context;private final Host host;private final boolean reuse;private OfflineRecognizer session;
 SpeechEngine(Context c,Host h){this(c,h,false);}
 SpeechEngine(Context c,Host h,boolean reusable){context=c;host=h;reuse=reusable;}
 void close(){if(session!=null){session.release();session=null;}}
 static boolean nonSpeechAnnotation(String text){String value=text.trim().toLowerCase(Locale.ROOT);if(value.length()<2)return false;boolean brackets=(value.startsWith("(")&&value.endsWith(")"))||(value.startsWith("[")&&value.endsWith("]"));if(!brackets)return false;value=value.substring(1,value.length()-1).trim();return Arrays.asList("music","müzik","upbeat music","instrumental music","müzik çalıyor").contains(value);}
 static String stamp(double seconds){long ms=Math.round(seconds*1000);return String.format(Locale.ROOT,"%02d:%02d:%02d,%03d",ms/3600000,(ms/60000)%60,(ms/1000)%60,ms%1000);}
 String read(File input,String language,double start,double end,File work)throws Exception {return read(input,language,start,end,work,false);}
 String read(File input,String language,double start,double end,File work,boolean srt)throws Exception {
  if(!Arrays.asList("tr","en").contains(language))throw new IOException("Unsupported speech language");host.check();
  File pcm=new File(work,"speech.pcm");List<String>args=new ArrayList<String>(Arrays.asList("ffmpeg","-v","error","-nostdin","-progress","pipe:1","-protocol_whitelist","file,pipe","-ss",Double.toString(start),"-i",input.getAbsolutePath()));if(end>=0){if(end<=start)throw new IOException("Invalid time range");args.addAll(Arrays.asList("-t",Double.toString(end-start)));}args.addAll(Arrays.asList("-vn","-ac","1","-ar","16000","-f","s16le","-y",pcm.getAbsolutePath()));host.run(args);host.check();
  OfflineWhisperModelConfig whisper=new OfflineWhisperModelConfig();whisper.setEncoder("speech/small-encoder.int8.onnx");whisper.setDecoder("speech/small-decoder.int8.onnx");whisper.setLanguage(language);whisper.setTask("transcribe");
  OfflineModelConfig model=new OfflineModelConfig();model.setWhisper(whisper);model.setTokens("speech/small-tokens.txt");model.setNumThreads(2);model.setProvider("cpu");
  OfflineRecognizerConfig config=new OfflineRecognizerConfig();config.setModelConfig(model);config.setDecodingMethod("greedy_search");config.setFeatConfig(new FeatureConfig(16000,80,0f));
  if(session==null){ActivityManager.MemoryInfo memory=new ActivityManager.MemoryInfo();((ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE)).getMemoryInfo(memory);if(memory.totalMem<3L*1024*1024*1024||memory.availMem<1536L*1024*1024)throw new IOException("speech_memory_low");session=new OfflineRecognizer(context.getAssets(),config);}else session.setConfig(config);
  OfflineRecognizer recognizer=session;RandomAccessFile audio=new RandomAccessFile(pcm,"r");StringBuilder result=new StringBuilder();int cue=0;
  try{long total=audio.length()/2,position=0;while(position<total){host.check();int count=(int)Math.min(28*16000,total-position);byte[]bytes=new byte[count*2];audio.seek(position*2);audio.readFully(bytes);float[]samples=new float[count];double energy=0;for(int i=0;i<count;i++){short value=(short)((bytes[i*2]&255)|(bytes[i*2+1]<<8));samples[i]=value/32768f;energy+=samples[i]*samples[i];}
    // Prefer a quiet cut near the end of a full chunk so words are not split.
    if(count>4*16000){
     // Decode utterances separately when a clear half-second pause is available.
     // Long repetitive passages can otherwise be collapsed by Whisper's decoder.
     int cut=0;for(int at=3*16000;at<count-8000;at+=1600){double e=0;for(int i=at;i<at+8000;i++)e+=samples[i]*samples[i];if(Math.sqrt(e/8000)<.0004){cut=at+4000;break;}}
     if(cut==0){double best=Double.MAX_VALUE;cut=count;for(int at=23*16000;at<count-1600;at+=1600){double e=0;for(int i=at;i<at+1600;i++)e+=samples[i]*samples[i];if(e<best){best=e;cut=at+800;}}}
     count=cut;samples=Arrays.copyOf(samples,count);energy=0;for(float v:samples)energy+=v*v;
    }
    host.progress(position/16000d,total/16000d);if(count>0&&Math.sqrt(energy/count)>.0004){OfflineStream stream=recognizer.createStream();try{stream.acceptWaveform(samples,16000);recognizer.decode(stream);host.check();String text=recognizer.getResult(stream).getText().trim();if(text.length()>0&&!nonSpeechAnnotation(text)){if(srt){result.append(++cue).append('\n').append(stamp(start+position/16000d)).append(" --> ").append(stamp(start+(position+count)/16000d)).append('\n').append(text.replaceAll("\\s+"," ")).append("\n\n");}else{if(result.length()>0)result.append('\n');result.append(text);}}}finally{stream.release();}}
    position+=count;
  }host.check();host.progress(total/16000d,total/16000d);return result.toString().trim();}finally{audio.close();if(!reuse)close();pcm.delete();}
 }
}
