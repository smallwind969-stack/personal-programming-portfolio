const fs=require('node:fs');
const M=require('./model.js');
const s=M.initial();
const object=(id,name,x,y,w,d,h,kind,color,angle=0,z=0)=>({id,name,x,y,w,d,h,z,angle,color,visible:true,zone:'room',kind});
const bathroom=s.objects.filter(o=>o.zone==='bath');
s.objects=[
object('teamdesk','开黑长桌 / 4人舒适·5人紧凑',.5,3.9,.8,4,.75,'desk','#a47f5f'),
object('bed','双人床 / 含床架占位',3.675,4.45,1.8,2.15,.45,'bed','#c8c2b5',-90),
object('sofa','双人沙发',3.75,2.25,2,.85,.8,'sofa','#84979c',-90),
object('wardrobe','入口窄衣柜',4.65,1.35,.6,.9,2.3,'cabinet','#a79581'),
...Array.from({length:5},(_,i)=>object('chair-'+i,'座位 '+(i+1),1.4,2.3+.8*i,.62,.62,.48,'box','#555f62')),
...bathroom];
// Sofa is horizontal; its renderer places the back on the positive local X edge.
const sofa=s.objects.find(o=>o.id==='sofa');sofa.w=.85;sofa.d=2;
M.parse(JSON.stringify(s));
for(const o of s.objects){const warnings=M.warnings(o,s);if(warnings.length)throw Error(o.name+': '+warnings.join(';'));}
fs.writeFileSync('开黑与双人生活-方案A.json',JSON.stringify(s,null,2));
const scale=100,ox=125,oy=80,px=x=>ox+x*scale,py=y=>oy+(6-y)*scale;
const esc=t=>t.replaceAll('&','&amp;').replaceAll('<','&lt;');
const text=(x,y,t,size=14,color='#344941')=>`<text x="${x}" y="${y}" text-anchor="middle" font-family="Microsoft YaHei, sans-serif" font-size="${size}" fill="${color}">${esc(t)}</text>`;
let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="920" height="840" viewBox="0 0 920 840"><rect width="920" height="840" fill="#f7f6f0"/>${text(375,34,'方案 A · 并排开黑 + 双人生活',24)}${text(375,59,'整体 5×6 m · 左下卫生间 3.3×1.7 m · 平面按比例绘制',12)}<rect x="${ox}" y="${oy}" width="500" height="600" fill="#eae7dd" stroke="#475b50" stroke-width="4"/><rect x="${px(0)}" y="${py(1.7)}" width="330" height="170" fill="#dce9e1" stroke="#669184" stroke-width="2"/>`;
for(const o of s.objects){const b=M.bounds(o);svg+=`<rect x="${px(b.minX)}" y="${py(b.maxY)}" width="${(b.maxX-b.minX)*scale}" height="${(b.maxY-b.minY)*scale}" rx="4" fill="${o.color}" stroke="#7b8b7c"/>`;if(o.id.startsWith('chair'))svg+=text(px(o.x),py(o.y)+5,o.name,11,'#ffffff');else if(o.id==='bed')svg+=text(px(o.x),py(o.y),'1.8 m 双人床',16);else if(o.id==='teamdesk')svg+=`<text x="${px(o.x)}" y="${py(o.y)}" text-anchor="middle" transform="rotate(-90 ${px(o.x)} ${py(o.y)})" font-family="Microsoft YaHei" font-size="14" fill="#fff">4 m 长桌 × 0.8 m 深</text>`;else if(o.id==='sofa')svg+=text(px(o.x),py(o.y)+5,'2 m 双人沙发',13);else if(o.id==='wardrobe')svg+=text(px(o.x),py(o.y)+5,'衣柜',11);}
svg+=`<rect x="${px(s.openings.entryX)}" y="${py(0)-4}" width="90" height="8" fill="#f7f6f0"/><rect x="${px(3.3)-4}" y="${py(s.openings.bathY+s.openings.bathW)}" width="8" height="75" fill="#f7f6f0"/><line x1="${px(.6)}" y1="${py(6)}" x2="${px(4.4)}" y2="${py(6)}" stroke="#699caa" stroke-width="7"/>${text(px(4.1),py(0)+25,'入口（暂估）')}${text(px(1.65),py(.15),'卫生间 3.3 × 1.7 m',14)}${text(px(2.2),py(3.2),'主通道',13)}${text(px(2.2),py(2.92),'约 0.89–1.04 m',11)}${text(px(3.75),py(3.1),'床侧与沙发之间约 0.88 m',11)}${text(px(3.75),py(5.7),'床侧到窗墙约 0.65 m',11)}${text(766,112,'暖灰 × 木色 × 雾蓝',17)}`;
const notes=['4 人：每位约 1 m 桌面','5 人：每位约 0.8 m 桌面','椅子占位 0.62×0.62 m','通道按椅子静态占位测算','移椅 / 起身时需要借用通道','床架总尺寸需实测校准','沙发沿卫生间隔墙背靠布置','入口衣柜暂估 0.9 m 宽','保留现有木门和灰色地砖','主机设备不计入方案','门扇开启范围尚未验证'];
notes.forEach((t,i)=>svg+=text(766,158+i*30,t,12));
svg+=text(460,752,'已确认：整体与卫生间尺寸。门窗、墙厚及家具实际尺寸仍需校准。',13);svg+=text(460,780,'这是空间设计方案；床、沙发、桌子位置是拟议布置，未还原为照片现状。',12);svg+='</svg>';
fs.writeFileSync('方案A-比例平面图.svg',svg);
console.log('PASS: proposed furniture fits room, does not overlap bathroom or other furniture; JSON validates.');
