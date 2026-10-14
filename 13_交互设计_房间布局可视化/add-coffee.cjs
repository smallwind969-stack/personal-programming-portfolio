const fs=require('node:fs');const assert=require('node:assert/strict');const M=require('./model.js');
const s=M.parse(fs.readFileSync(process.argv[2]||'开黑与双人生活-方案A.json','utf8'));
const table={id:'coffee',name:'沙发咖啡圆桌 Ø50cm',x:4.05,y:3.15,w:.5,d:.5,h:.55,z:0,angle:0,color:'#b38c65',visible:true,zone:'room',kind:'box',shape:'round'};
const currentSofa=s.objects.find(o=>o.id==='sofa'),currentBed=s.objects.find(o=>o.id==='bed');
if(currentSofa.y>4.5){currentSofa.angle=90;table.w=table.d=.4;table.name='沙发咖啡圆桌 Ø40cm';table.x=currentSofa.x+.3;table.y=(M.bounds(currentSofa).minY+M.bounds(currentBed).maxY)/2;}
s.objects.push(table);M.parse(JSON.stringify(s));
assert.equal(s.objects.filter(o=>o.id.startsWith('chair')).length,5);
assert.deepEqual(M.warnings(table,s),[],table.name);
const sofa=M.bounds(s.objects.find(o=>o.id==='sofa')),bed=M.bounds(s.objects.find(o=>o.id==='bed')),t=M.bounds(table);
const sofaGap=currentSofa.y>4.5?sofa.minY-t.maxY:t.minY-sofa.maxY,bedGap=currentSofa.y>4.5?t.minY-bed.maxY:bed.minY-t.maxY;
assert.ok(sofaGap>=.1);assert.ok(bedGap>=.1);assert.ok(t.minX>=3.7);
fs.writeFileSync('方案A-沙发咖啡圆桌.json',JSON.stringify(s,null,2));
console.log('PASS: 5 gaming seats retained, table outside main aisle, table has no overlap. Sofa gap '+sofaGap.toFixed(3)+'m; bed gap '+bedGap.toFixed(3)+'m.');
