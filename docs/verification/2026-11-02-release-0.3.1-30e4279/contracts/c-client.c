#include "iso532.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
static double x[4800],n[50],spec[12000],bark[240],timegrid[50];
static int sentinel(double *p,size_t count){for(size_t i=0;i<count;i++)if(p[i]!=-1234567.25)return 0;return 1;}
static void fill(void){for(int i=0;i<50;i++)n[i]=timegrid[i]=-1234567.25;for(int i=0;i<12000;i++)spec[i]=-1234567.25;for(int i=0;i<240;i++)bark[i]=-1234567.25;}
int main(void){int failed=0;printf("{\"case\":\"header_constant\",\"pass\":%s,\"value\":%d}\n",ISO532_ERR_NONFINITE_INPUT==4?"true":"false",ISO532_ERR_NONFINITE_INPUT);double vals[]={NAN,INFINITY,-INFINITY};int indices[]={0,2400,4799};for(int tv=0;tv<2;tv++)for(int v=0;v<3;v++)for(int pos=0;pos<3;pos++){memset(x,0,sizeof x);x[indices[pos]]=vals[v];fill();int code=tv?iso532_loudness_zwtv(x,4800,48000,0,n,spec,bark,timegrid):iso532_loudness_zwst(x,4800,48000,0,n,spec,bark);int ok=code==4&&sentinel(n,50)&&sentinel(spec,12000)&&sentinel(bark,240)&&sentinel(timegrid,50);failed+=!ok;printf("{\"case\":\"sentinel/%d/%d/%d\",\"pass\":%s,\"code\":%d,\"checked_doubles\":12340}\n",tv,v,indices[pos],ok?"true":"false",code);}
size_t lengths[]={4800,4801,4823,4824,4825,4895,4896,4897,24013,47905,47916,47927,47928,47952,47999,48000};for(int i=0;i<16;i++){size_t want=((lengths[i]+23)/24+3)/4,got=iso532_zwtv_out_frames(lengths[i]);int ok=want==got;failed+=!ok;printf("{\"case\":\"grid/%zu\",\"pass\":%s,\"expected\":%zu,\"actual\":%zu}\n",lengths[i],ok?"true":"false",want,got);}
for(int tv=0;tv<2;tv++)for(int scenario=0;scenario<7;scenario++){
 memset(x,0,sizeof x);size_t len=4800;double fs=48000;int expected=4;
 if(scenario==0){x[0]=NAN;fs=44100;expected=3;}
 if(scenario==1){x[0]=NAN;len=4799;expected=2;}
 if(scenario==2){x[51]=NAN;x[3300]=INFINITY;}
 if(scenario>=3){double val=scenario==3?nextafter(0.,1.):scenario==4?0.:scenario==5?-0.:1e300;for(int i=0;i<4800;i++)x[i]=val;}
 fill();int code=tv?iso532_loudness_zwtv(x,len,fs,0,n,spec,bark,timegrid):iso532_loudness_zwst(x,len,fs,0,n,spec,bark);int ok=scenario>=3?code!=4:code==expected;
 if(scenario<3)ok=ok&&sentinel(n,50)&&sentinel(spec,12000)&&sentinel(bark,240)&&sentinel(timegrid,50);
 failed+=!ok;printf("{\"case\":\"boundary/%d/%d\",\"pass\":%s,\"actual_code\":%d}\n",tv,scenario,ok?"true":"false",code);
}

for(int z=0;z<3;z++){
 int idx=z==0?0:z==1?101:4799;Iso532StreamFrame a[52],b[52];size_t na=0,nb=0,tail=0;
 memset(x,0,sizeof x);Iso532Stream *sa=iso532_stream_new(0),*sb=iso532_stream_new(0);
 int rc=iso532_stream_push(sa,x,4800,a,52,&na);rc|=iso532_stream_flush(sa,a+na,1,&tail);na+=tail;
 x[idx]=NAN;rc|=iso532_stream_push(sb,x,4800,b,52,&nb);rc|=iso532_stream_flush(sb,b+nb,1,&tail);nb+=tail;
 uint32_t residual=iso532_stream_residual_flags(sb),residual_again=iso532_stream_residual_flags(sb);int ok=rc==0&&na==nb&&na==50,flag_count=0;size_t flag_index=0;
 for(size_t i=0;i<na&&i<nb;i++){ok=ok&&memcmp(&a[i].n,&b[i].n,sizeof(double))==0&&memcmp(&a[i].n_phon,&b[i].n_phon,sizeof(double))==0&&a[i].t_frame_index==b[i].t_frame_index;if(b[i].flags&ISO532_STREAM_FLAG_NONFINITE_INPUT){flag_count++;flag_index=i;}}
 ok=ok&&(z==2?(flag_count==0&&residual==2&&residual_again==2):(flag_count==1&&flag_index==(size_t)z&&residual==0));failed+=!ok;
 printf("{\"case\":\"stream_nan/%d\",\"pass\":%s,\"frames\":%zu,\"flag_count\":%d,\"flag_index\":%zu,\"residual\":%u,\"residual_again\":%u}\n",idx,ok?"true":"false",na,flag_count,flag_index,residual,residual_again);
 iso532_stream_free(sa);iso532_stream_free(sb);
}
return failed?1:0;}
