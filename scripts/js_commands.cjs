#!/usr/bin/env node
'use strict';
/** Static arrow-command DSL. User source is NEVER evaluated or imported. */
const acorn = require('./vendor/acorn.cjs');
const fs = require('node:fs');
const path = require('node:path');
const MAX_SOURCE = 65536, MAX_INPUT = 16384, MAX_STEPS = 64;
const own = (o,k) => Object.prototype.hasOwnProperty.call(o,k);
const BAD_KEYS = new Set(['__proto__','prototype','constructor']);
const BUILTINS = Object.freeze({
  task: {signature:'task(objective)', description:'执行一项明确的开发任务', min:1, max:1, params:['objective']},
  always: {signature:'always()', description:'持续开发；自动恢复需真实调度能力', min:0, max:0, params:[]},
  run: {signature:'run(interval = "1h")', description:'定时续作；实际频率取决于宿主', min:0, max:1, params:['interval']},
  status: {signature:'status()', description:'只读查看当前状态', min:0, max:0, params:[]},
  stop: {signature:'stop()', description:'停止当前项目的自动续作', min:0, max:0, params:[]},
  help: {signature:'help()', description:'查看帮助', min:0, max:0, params:[]},
  open: {signature:'open(target?)', description:'按项目名称、ID、路径查看进度', min:0, max:1, params:['target']},
  handoff: {signature:'handoff(target?)', description:'保存会话交接', min:0, max:1, params:['target']},
  watch: {signature:'watch(optionsOrAction?)', description:'后台续作；可传选项对象或 "doctor/status/stop/resume"', min:0, max:1, params:['optionsOrAction']},
  sessions: {signature:'sessions(optionsOrAction?)', description:'会话数量和轮数管理；或 "status/stop"', min:0, max:1, params:['optionsOrAction']},
  sync: {signature:'sync(optionsOrAction?)', description:'安全同步与低额度动作；或 "status/stop"', min:0, max:1, params:['optionsOrAction']},
  subagent: {signature:'subagent(names?)', description:'按实际名称选择子代理；不是创建代理', min:0, max:1, params:['names']},
});
function fail(message) { throw new Error(message); }
function guard(text,max=MAX_INPUT) { if(typeof text!=='string'||text.length>max) fail(`Input must be text of at most ${max} UTF-16 units`); }
function strip(raw) { guard(raw); return raw.trim().replace(/^[@$]?continuous-development(?=\s|$)\s*/, ''); }
function parse(text) { try { return acorn.parse(text,{ecmaVersion:2022,sourceType:'script'}); } catch(e) { fail(`JS syntax: ${e.message}`); } }
function validId(name) { return /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(name) && !BAD_KEYS.has(name); }
function value(node, env, check=false, depth=0) {
  if(!node || depth>16) fail('Unsupported or deeply nested argument');
  const sub=n=>value(n,env,check,depth+1);
  switch(node.type) {
    case 'Literal':
      if(node.regex || node.bigint || !['string','number','boolean','object'].includes(typeof node.value) || (typeof node.value==='number'&&!Number.isFinite(node.value))) fail('Only finite JSON-like literal values supported');
      return node.value;
    case 'Identifier':
      if(!own(env,node.name)) fail(`Unknown parameter: ${node.name}`);
      return env[node.name];
    case 'UnaryExpression':
      if(!['-','+'].includes(node.operator)||node.argument.type!=='Literal'||typeof node.argument.value!=='number') fail('Only signed number literals supported');
      return node.operator==='-' ? -sub(node.argument):sub(node.argument);
    case 'ArrayExpression':
      if(node.elements.some(x=>!x||x.type==='SpreadElement')) fail('No array holes or spread');
      return node.elements.map(sub);
    case 'ObjectExpression': {
      const result=Object.create(null);
      for(const p of node.properties) {
        if(p.type!=='Property'||p.computed||p.method||p.kind!=='init') fail('Only literal object properties supported');
        const key=p.key.type==='Identifier'?p.key.name:p.key.value;
        if(typeof key!=='string'||BAD_KEYS.has(key)||own(result,key)) fail('Invalid, duplicate or unsafe object key');
        result[key]=sub(p.value);
      }
      return result;
    }
    case 'TemplateLiteral': {
      let out='';
      for(let i=0;i<node.quasis.length;i++) {
        out+=node.quasis[i].value.cooked;
        if(i<node.expressions.length) {
          const v=sub(node.expressions[i]);
          if(!check && typeof v==='object'&&v!==null) fail('Template placeholders must be primitive parameters');
          out+=check?'':String(v);
        }
      }
      if(out.length>MAX_SOURCE) fail('Expanded template too long');
      return out;
    }
    default: fail(`Unsupported argument syntax: ${node.type}. No executable JS arguments.`);
  }
}
function directCall(node,env,check=false) {
  if(!node||node.type!=='CallExpression'||node.callee.type!=='Identifier'||node.optional||node.arguments.some(x=>x.type==='SpreadElement')) fail('Only direct command calls allowed');
  if(own(env,node.callee.name))fail('A parameter cannot be used as a command function');
  return {command:node.callee.name,args:node.arguments.map(n=>value(n,env,check))};
}
function metadata(d) { return {name:d.name,signature:d.signature,description:d.description,params:d.params.map(p=>({...p})),source:'custom'}; }
function parseDefinitions(source) {
  guard(source,MAX_SOURCE);
  const ast=parse(source), registry=new Map();
  if(ast.body.length>100) fail('At most 100 arrow declarations');
  for(const statement of ast.body) {
    if(statement.type==='EmptyStatement') continue;
    if(statement.type!=='VariableDeclaration'||statement.kind!=='const') fail('Only const name = (...) => ... declarations allowed');
    for(const d of statement.declarations) {
      if(d.id.type!=='Identifier'||!validId(d.id.name)||!d.init||d.init.type!=='ArrowFunctionExpression'||d.init.async) fail('Expected non-async const arrow function with a simple name');
      const name=d.id.name;
      if(own(BUILTINS,name)||['commands','suggest'].includes(name)) fail(`Reserved builtin name: ${name}`);
      if(registry.has(name)) fail(`Duplicate declaration: ${name}`);
      const seen=new Set(),params=[];
      for(const p of d.init.params) {
        let id=p,defaultNode=null;
        if(p.type==='AssignmentPattern') {id=p.left;defaultNode=p.right;}
        if(id.type!=='Identifier'||!validId(id.name)||seen.has(id.name)) fail('Only unique simple parameters; no destructuring/rest');
        seen.add(id.name);
        const item={name:id.name,required:!defaultNode};
        if(defaultNode) item.defaultValue=value(defaultNode,Object.create(null));
        params.push(item);
      }
      let calls=[];
      if(d.init.body.type==='BlockStatement') {
        const body=d.init.body.body.filter(s=>s.type!=='EmptyStatement');
        for(let i=0;i<body.length;i++) {
          const s=body[i];
          if(s.type==='ReturnStatement') {
            if(i!==body.length-1) fail('Statements after return are not allowed');
            calls.push(s.argument);
          } else if(s.type==='ExpressionStatement') calls.push(s.expression);
          else fail(`Unsupported statement: ${s.type}`);
        }
      } else calls=[d.init.body];
      if(!calls.length) fail('An alias must contain at least one command call');
      const env=Object.create(null);for(const p of params)env[p.name]=null;
      calls.forEach(c=>directCall(c,env,true));
      const before=source.slice(0,statement.start);
      const commentStart=before.lastIndexOf('/**');
      const match=commentStart<0?null:before.slice(commentStart).match(/^\/\*\*([\s\S]*?)\*\/\s*$/);
      const description=match?match[1].replace(/\*/g,'').trim().slice(0,180):'自定义箭头函数命令';
      const signature=`${name}(${params.map(p=>p.name+(p.required?'':` = ${JSON.stringify(p.defaultValue)}`)).join(', ')})`;
      registry.set(name,{name,params,calls,description,signature});
    }
  }
  if(registry.size>100) fail('At most 100 aliases');
  const verifiedDepth=new Map();
  function visit(name,stack=[]) {
    if(stack.includes(name)||stack.length>=8) fail('Recursive or excessively deep aliases are not allowed');
    if(verifiedDepth.has(name)){if(stack.length+verifiedDepth.get(name)>8)fail('Alias depth limit');return verifiedDepth.get(name);}
    let height=1;
    for(const c of registry.get(name).calls) {
      const target=c.callee.name;
      if(!registry.has(target)&&!own(BUILTINS,target)) fail(`Unknown command: ${target}`);
      if(registry.has(target))height=Math.max(height,1+visit(target,[...stack,name]));
    }
    verifiedDepth.set(name,height);return height;
  }
  for(const name of registry.keys())visit(name);
  return registry;
}
function expand(text,registry) {
  guard(text); const ast=parse(strip(text));
  if(ast.body.length!==1||ast.body[0].type!=='ExpressionStatement') fail('Provide one command call');
  const first=directCall(ast.body[0].expression,Object.create(null));
  const steps=[];
  function emit(call,stack=[]) {
    if(stack.length>8||steps.length>=MAX_STEPS) fail('Expansion limit exceeded');
    if(registry.has(call.command)) {
      const d=registry.get(call.command);if(stack.includes(d.name))fail('Recursive alias');
      if(call.args.length>d.params.length)fail(`Too many arguments for ${d.signature}`);
      const env=Object.create(null);
      d.params.forEach((p,i)=>{
        if(i<call.args.length)env[p.name]=call.args[i];
        else if(!p.required)env[p.name]=p.defaultValue;
        else fail(`Missing argument ${p.name} for ${d.signature}`);
      });
      d.calls.forEach(c=>emit(directCall(c,env),[...stack,d.name]));
    } else if(own(BUILTINS,call.command)) {
      const spec=BUILTINS[call.command];
      if(call.args.length<spec.min||call.args.length>spec.max)fail(`Wrong argument count for ${spec.signature}`);
      if(call.command==='task' && (typeof call.args[0]!=='string'||!call.args[0].trim()))fail('task() requires a nonempty objective string');
      steps.push({...call,execution:'not_executed'});
    } else fail(`Unknown command: ${call.command}`);
  }
  emit(first);
  return {schema:'continuous-development.js-plan.v1',kind:'plan',alias:first.command,steps,execution:'not_executed',requires_host_execution:true};
}
function list(registry) {
  return [ ...[...registry.values()].map(metadata),
    ...Object.entries(BUILTINS).map(([name,s])=>({name,signature:s.signature,description:s.description,params:s.params.map(name=>({name})),source:'builtin'}))
  ].sort((a,b)=>a.name.localeCompare(b.name));
}
// Tolerant delimiter scanner: this only determines a signature, NEVER executes input.
function scanCall(text) {
  const m=text.match(/^([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/);if(!m)return null;
  let stack=['('],quote=null,escape=false,index=0;
  for(let i=m[0].length;i<text.length;i++) {
    const c=text[i];
    if(quote){if(escape)escape=false;else if(c==='\\')escape=true;else if(c===quote)quote=null;continue;}
    if(['"',"'",'`'].includes(c)){quote=c;continue;}
    if('([{'.includes(c))stack.push(c);
    else if(')]}'.includes(c)) {const opening=stack.pop();if('([{'.indexOf(opening)!==')]}'.indexOf(c))return null;if(!stack.length)return null;}
    else if(c===','&&stack.length===1)index++;
  }
  return {name:m[1],activeParameter:index,stack,quote};
}
function complete(raw,registry,cursor=raw.length) {
  guard(raw);if(!Number.isInteger(cursor)||cursor<0||cursor>raw.length)fail('Invalid UTF-16 cursor offset');
  const left=raw.slice(0,cursor),leading=left.length-left.trimStart().length;
  const prefix=left.slice(leading).match(/^[@$]?continuous-development(?=\s|$)\s*/);
  const base=leading+(prefix?prefix[0].length:0), body=left.slice(base), entries=list(registry);
  const result={schema:'continuous-development.completion.v1',kind:'suggestions',execution:'not_executed',read_only:true,inputText:raw,items:[],signature:null,cursorEncoding:'utf-16'};
  const call=scanCall(body);
  if(call) {
    const d=entries.find(x=>x.name===call.name);
    if(d)result.signature={label:d.signature,description:d.description,parameters:d.params,activeParameter:call.activeParameter};
    const options={watch:{every:'60s',retry:3,threshold:1},sessions:{initial:20,limit:15,rounds:15,scope:'host'},sync:{every:'5m',threshold:1,on_low:'checkpoint-push-pause',remotes:['github','gitee']}};
    const actions={watch:['doctor','status','stop','resume'],sessions:['status','stop'],sync:['status','stop']};
    const quoted=body.match(/^[A-Za-z_$][A-Za-z0-9_$]*\s*\(\s*(['"])([A-Za-z_-]*)$/);
    if(quoted && actions[call.name]) {
      const key=quoted[2], start=cursor-key.length;
      result.items=actions[call.name].filter(x=>x.startsWith(key)).map(x=>({name:x,label:x,detail:'只补全动作文字；不执行',source:'action',insertText:x,replace:{start,end:cursor+(raw.slice(cursor).match(/^[A-Za-z_-]*/)||[''])[0].length}}));
    } else if(!call.quote && options[call.name]) {
      const tail=body.match(/(?:[({,])\s*([A-Za-z_][A-Za-z0-9_]*|)$/);
      const js=call.stack.length===2&&call.stack[1]==='{';
      const legacy=call.stack.length===1;
      if(tail && (js||legacy)) {
        const key=tail[1], start=cursor-key.length;
        result.items=Object.entries(options[call.name]).filter(([name])=>name.startsWith(key)).map(([name,v])=>({
          name,label:name,detail:'默认 '+JSON.stringify(v),source:'option',
          insertText:name+(js?': ':'=')+JSON.stringify(v),replace:{start,end:cursor+(raw.slice(cursor).match(/^[A-Za-z0-9_]*/)||[''])[0].length}
        }));
      }
    }
    return result;
  }
  if(!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(body)&&body!=='')return result;
  const partial=body, suffix=raw.slice(cursor).match(/^[A-Za-z0-9_$]*/)[0];
  result.items=entries.filter(d=>d.name.toLowerCase().startsWith(partial.toLowerCase())).map(d=>({
    ...d,label:d.signature,detail:d.description,insertText:d.name+'()',
    insertSnippet:d.name+'('+d.params.map((p,i)=>'${'+(i+1)+':'+p.name+'}').join(', ')+')',
    replace:{start:base,end:cursor+suffix.length},
  }));
  return result;
}
function inspect(raw,registry) {
  const text=strip(raw);
  if(/^const\b/.test(text)) {
    const found=parseDefinitions(text);
    return {kind:'definitions',definitions:[...found.values()].map(metadata),registered:false,execution:'not_executed',read_only:true};
  }
  if(/^commands\s*\(\s*\)\s*;?$/.test(text))return complete('',registry);
  if(/^suggest\s*\(/.test(text)) {
    const ast=parse(text), node=ast.body[0]?.expression;
    if(ast.body.length!==1||!node||node.type!=='CallExpression'||node.callee.name!=='suggest'||node.arguments.length>1)fail('Use suggest("prefix")');
    const p=node.arguments.length?value(node.arguments[0],Object.create(null)):'';
    if(typeof p!=='string')fail('suggest() expects a string');
    return complete(p,registry);
  }
  if(/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(text)||text==='')return complete(raw,registry);
  if(scanCall(text))return complete(raw,registry);
  return expand(text,registry);
}
module.exports={parseDefinitions,expand,complete,inspect,BUILTINS};
if(require.main===module) {
  try {
    const bytes=fs.readFileSync(0);if(bytes.length>150000)fail('Request too large');
    const req=JSON.parse(bytes.toString('utf8'));
    if(!req||typeof req!=='object'||Array.isArray(req))fail('Expected JSON request');
    let src='';
    if(own(req,'source')){src=req.source;guard(src,MAX_SOURCE);}
    else {
      const file=req.registryPath||path.join(__dirname,'../commands/shortcuts.js');
      const fallback=path.join(__dirname,'../commands/shortcuts.example.js');
      const chosen=fs.existsSync(file)?file:fallback;
      if(fs.statSync(chosen).size>MAX_SOURCE*4)fail('Registry too large');
      src=fs.readFileSync(chosen,'utf8');
    }
    const registry=parseDefinitions(src);
    let res;
    switch(req.action||'inspect') {
      case 'list':res={kind:'catalogue',commands:list(registry),execution:'not_executed'};break;
      case 'definitions':res=inspect(req.text||'',registry);break;
      case 'complete':res=complete(req.text||'',registry,req.cursor===undefined?(req.text||'').length:req.cursor);break;
      case 'inspect':res=inspect(req.text||'',registry);break;
      default:fail('Unknown request action');
    }
    process.stdout.write(JSON.stringify(res,null,2)+'\n');
  } catch(e) {
    process.stdout.write(JSON.stringify({kind:'error',error:e.message,execution:'not_executed',read_only:true})+'\n');process.exitCode=2;
  }
}
