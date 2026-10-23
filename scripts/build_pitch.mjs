import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime='C:/Users/campong/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const skill='C:/Users/campong/.codex/plugins/cache/openai-primary-runtime/presentations/26.1020.11127/skills/presentations';
const {Presentation,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
const data=JSON.parse(await fs.readFile(path.join(root,'web/pitch/deck.json'),'utf8'));
const tmp=path.join(root,'paper/_build/pitch');
const out=path.join(root,'output/pitch');
await fs.mkdir(tmp,{recursive:true});await fs.mkdir(out,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const font='DejaVu Sans', dark='#07121C', white='#F4F8F5', mint='#66E5BD', ink='#102D2C', mute='#AFC1C6';
const bg=await fs.readFile(path.join(root,'web/pitch/assets/compute-background.png'));
const logo=await fs.readFile(path.join(root,'brand/logo-dark-transparent-3.png'));

function text(slide,value,x,y,w,h,size=28,color=white,bold=false,name='text'){
  const shape=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={fontSize:size,typeface:font,color,bold,verticalAlignment:'top',alignment:'left',insets:0,autoFit:'none',wrap:'square'};
  return shape;
}
function addMetrics(slide,d,c){d.metrics.forEach(([number,unit,description],j)=>{
  const x=72+j*390;
  text(slide,number,x,265,365,110,number.length>8?58:72,c.accent,true,'metric');
  text(slide,unit,x,388,365,65,25,c.ink,true);
  text(slide,description,x,470,350,95,24,c.muted);
});}
if(!process.argv.includes('--finalize-only'))for(let i=0;i<data.slides.length;i++){
 const d=data.slides[i],s=p.slides.add();
 const c=d.light?{ink,muted:'#486762',accent:'#087B65'}:{ink:white,muted:mute,accent:mint};
 s.background.fill=d.light?'#F3F6EF':dark;
 if(d.kind==='cover'||d.kind==='ask'){
  s.images.add({blob:bg,contentType:'image/png',alt:'Conceptual compute network artwork, not deployed PASADHI hardware',fit:'cover',position:{left:0,top:0,width:1280,height:720}});
  if(d.kind==='cover'){
  s.images.add({blob:logo,contentType:'image/png',alt:'PASADHI original logo',fit:'contain',position:{left:68,top:40,width:88,height:72}});
  text(s,'PASADHI',176,61,440,50,32,white,true);
  }else{s.shapes.add({geometry:'rect',position:{left:0,top:0,width:745,height:720},fill:dark,line:{fill:'none',width:0}});}
 }
 if(d.kind==='cover'){
  text(s,'AI compute on the\ncomputers you\nalready own',72,185,730,275,62,white,true,'title');
  text(s,'PASADHI · private compute\nfor existing office fleets',72,484,550,90,26,mute);
 }else{
  text(s,d.title,72,65,1136,132,46,c.ink,true,'title');
  if(d.kind==='product'){
   text(s,d.subtitle,72,188,1136,40,27,c.accent,true);
   s.images.add({blob:await fs.readFile(path.join(root,'web/pitch/assets/system.png')),contentType:'image/png',alt:'PASADHI target system architecture; distributed plane remains roadmap',fit:'contain',position:{left:92,top:242,width:1096,height:345}});
  }else if(d.metrics){addMetrics(s,d,c);
  }else if(d.kind==='chart'){
   text(s,d.big,72,252,575,110,54,mint,true);
   text(s,d.subtitle,72,380,515,130,28,white);
   const ch=s.charts.add('bar',{position:{left:660,top:228,width:535,height:345},categories:d.chart.categories,series:[{name:'Time to first token (s)',values:d.chart.values,fill:mint}],hasLegend:false,barOptions:{direction:'column',gapWidth:100},chartFill:dark,plotAreaFill:dark,
      xAxis:{textStyle:{fontSize:18,fill:white},line:{fill:'#335255',width:1}},
      yAxis:{min:0,max:125,title:'seconds',textStyle:{fontSize:16,fill:mute},majorGridlines:{fill:'#284047',width:1}},
      dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00',textStyle:{fontSize:20,fill:white}}});
   applyPresentationChartFont(ch,{fontFamily:font});
  }else if(d.table){
   const values=d.table;
   const cols=values[0].length;
   const widths=d.kind==='budget'?[650,250,236]:d.kind==='runway-research'?[310,300,526]:cols===4?[270,270,280,316]:[240,370,526];
   const table=s.tables.add({rows:values.length,columns:cols,left:72,top:225,width:1136,height:values.length>5?355:320,columnWidths:widths,values});
   for(let r=0;r<values.length;r++)for(let col=0;col<cols;col++){
    const cell=table.getCell(r,col);cell.fill=r===0?(d.light?'#D5E7DD':'#163C3D'):(d.light?'#F3F6EF':dark);cell.text.style={fontSize:23,typeface:font,color:c.ink,bold:r===0,insets:10,verticalAlignment:'middle'};
   }
   table.borders.assign({fill:'#BED5CA',width:1,style:'solid'});
  }else if(d.kind==='focus'){
   text(s,d.big,72,230,665,305,55,c.accent,true);
   text(s,d.subtitle,778,252,420,285,29,c.ink);
  }else if(d.kind==='market'){
   text(s,d.big,72,255,1136,120,66,mint,true);
   text(s,d.subtitle,72,402,1080,110,34,white);
  }else if(d.kind==='steps'||d.kind==='roadmap'){
   d.items.forEach(([num,label,body],j)=>{
    const x=72+j*390;
    text(s,num,x,247,355,65,28,c.accent,true);
    text(s,label,x,325,355,85,35,c.ink,true);
    text(s,body,x,430,355,140,26,c.muted);
   });
  }else if(d.kind==='team'){
   text(s,d.big,72,215,1120,145,54,mint,true);
   text(s,d.subtitle,72,385,1110,65,28,white);
   d.items.forEach(([label,body],j)=>{const x=72+j*580;text(s,label,x,473,545,45,26,mint,true);text(s,body,x,525,545,70,25,mute);});
  }else if(d.kind==='ask'){
   text(s,d.subtitle,72,228,730,95,32,mint,true);
   d.items.forEach(([label,body],j)=>{text(s,label,72,350+j*120,550,45,25,white,true);text(s,body,72,397+j*120,560,66,23,mute);});
  }else if(d.kind==='academic'){
   text(s,d.big,72,235,560,220,51,c.accent,true);
   d.items.forEach(([label,body],j)=>{text(s,label,690,233+j*110,510,40,25,c.accent,true);text(s,body,690,275+j*110,510,70,24,c.ink);});
  }else{
   d.items.forEach(([label,body],j)=>{text(s,label,72,235+j*114,310,80,27,c.accent,true);text(s,body,420,235+j*114,780,90,27,c.ink);});
  }
 }
 text(s,d.takeaway,72,613,1115,62,19,c.muted,false,'disclosure');
 text(s,`PASADHI  ·  ${i>=data.coreCount?'Research appendix':'Investor pitch'}  ·  23 Oct 2026`,72,684,1050,20,14,c.muted);
 text(s,String(i+1).padStart(2,'0'),1168,680,42,25,18,c.accent,true,'page');
 s.speakerNotes.text=d.notes+'\n\nSources and claim boundaries:\n'+d.sources.join('\n')+'\n\nAll commercial prices are proposals or model outputs, not customer revenue. USD conversion: 1 USD = 33.65 original local units, BOT reference 22 October 2026.';
 const image=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await image.arrayBuffer()));
 if((i+1)%3===0)console.log(`Rendered ${i+1}/${data.slides.length}`);
}
const candidate=path.join(tmp,'candidate.pptx');
if(!process.argv.includes('--finalize-only'))await (await PresentationFile.exportPptx(p)).save(candidate);
const tableOwners=data.slides.flatMap((d,i)=>d.table?[i+1]:[]);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(out,'PASADHI-pitch-2026-r2.pptx'),pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:data.slides.length,requiredNativeChartOwnerSlides:[6],materializeLiteralChartWorkbooks:true,tableArithmeticContracts:[{slide:20,table:1,label_column:0,total_row:6,value_columns:[1],component_rows:[1,2,3,4,5]}],requiredNativeTableOwnerSlides:tableOwners,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(tmp,'validation-r2.json')});
console.log(JSON.stringify(result));
await fs.copyFile(path.join(out,'PASADHI-pitch-2026-r2.pptx'),path.join(root,'web/download/PASADHI-pitch-2026.pptx'));
console.log('Final editable PPTX exported and staged for website.');
