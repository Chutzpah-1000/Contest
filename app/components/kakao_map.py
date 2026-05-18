from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Final

import numpy as np
import streamlit as st

if TYPE_CHECKING:
    import pandas as pd

SEOUL_LAT: float = 37.5665
SEOUL_LNG: float = 126.9780
DEFAULT_ZOOM: int = 8
SEARCH_ZOOM: int = 4
MAX_SUPPLY_PIN_W: float = 28.0
MIN_SUPPLY_PIN_W: float = 14.0
SUPPLY_SCALE: float = 90.0
MAX_PARK_RADIUS: float = 14.0
MIN_PARK_RADIUS: float = 5.0
PARK_AREA_SCALE: float = 200_000.0
MAX_FLOW_WEIGHT: float = 7.0
MIN_FLOW_WEIGHT: float = 2.0
FLOW_TON_SCALE: float = 30.0

# JS-side performance tuning (Round 10): viewport culling on `idle` event.
#   - FLOW_HIDE_LEVEL: 줌 레벨이 이 값 이상이면 매칭 폴리라인 일괄 숨김 (시 전체 줌아웃 클러터 방지).
#   - IDLE_THROTTLE_MS: idle 이벤트 후 컬링 실행을 지연시켜 연속 팬·줌 시 작업 폭주 차단.
_JS_FLOW_HIDE_LEVEL: Final[int] = 8
_JS_IDLE_THROTTLE_MS: Final[int] = 100

_SUPPLIER_COLS: list[str] = [
    "supplier_id",
    "name",
    "address",
    "latitude",
    "longitude",
    "daily_avg_supply_ton",
    "water_quality_grade",
    "report_status",
    "reportable",
    "geo_method",
]
_SIDE_PANEL_LIMIT: int = 500
_PARK_COLS: list[str] = ["demand_id", "name", "latitude", "longitude", "area_m2"]
_ROAD_COLS: list[str] = ["demand_id", "name", "centroid_lat", "centroid_lng", "length_m"]
_FLOW_COLS: list[str] = ["supplier_id", "demand_id", "ton_per_day"]

# Naver-style map UI: side panel (supplier list / detail) + pin markers + zoom controls + legend.
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;}
#app{display:flex;height:100%;background:#F7F7F5;}

/* ── Side panel ── */
#side-panel{width:272px;flex-shrink:0;display:flex;flex-direction:column;background:#fff;
  border-right:1px solid #E4E4E0;overflow:hidden;}
.panel-hdr{padding:11px 14px 9px;border-bottom:1px solid #E4E4E0;display:flex;align-items:center;gap:8px;background:#fff;}
.panel-title{font-size:12px;font-weight:700;color:#111;letter-spacing:.01em;flex:1;}
.cnt-badge{font-size:10px;color:#fff;background:#0071E3;border-radius:10px;padding:1px 6px;font-weight:700;}
.back-btn{background:none;border:none;cursor:pointer;font-size:11px;color:#0071E3;font-weight:600;padding:0;}
.filter-tabs{display:flex;gap:1px;background:#E4E4E0;border-radius:4px;padding:1px;}
.filter-tab{font-size:10px;font-weight:600;padding:3px 7px;border-radius:3px;cursor:pointer;
  border:none;background:transparent;color:#888;line-height:1;}
.filter-tab.active{background:#fff;color:#111;}

/* List view */
#list-view{display:flex;flex-direction:column;height:100%;}
#stats-bar{padding:6px 14px;border-bottom:1px solid #E4E4E0;font-size:11px;color:#888;background:#F7F7F5;flex-shrink:0;}
#stats-bar b{color:#1D7F5F;}
#sup-list{flex:1;overflow-y:auto;}
.sup-item{padding:9px 13px;border-bottom:1px solid #F0F0EE;cursor:pointer;display:flex;gap:8px;align-items:flex-start;}
.sup-item:hover{background:#F7F7F5;}
.sup-item.active{background:#EEF5FF;}
.sup-rank{width:17px;height:17px;border-radius:50%;font-size:9px;font-weight:700;display:flex;
  align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;color:#fff;}
.sup-rank.m{background:#3b82f6;}.sup-rank.u{background:#ef4444;}
.sup-info{flex:1;min-width:0;}
.sup-name{font-size:12px;font-weight:600;color:#111;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sup-ton{font-size:10px;color:#1D7F5F;font-weight:600;margin-top:2px;}
.sup-addr{font-size:10px;color:#888;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

/* Detail view */
#detail-view{display:none;flex-direction:column;height:100%;}
#detail-content{flex:1;overflow-y:auto;}
.d-body{padding:14px;}
.d-name{font-size:14px;font-weight:700;color:#111;line-height:1.35;margin-bottom:3px;}
.d-addr{font-size:11px;color:#666A70;margin-bottom:12px;}
.d-slbl{font-size:10px;font-weight:600;color:#666A70;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px;}
.d-sval{font-size:24px;font-weight:700;color:#1D7F5F;line-height:1.1;}
.d-sunit{font-size:11px;color:#666A70;font-weight:400;}
.d-meta{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:13px;}
.d-mlbl{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
.d-mval{font-size:12px;color:#111;font-weight:600;margin-top:2px;}
.d-badge{display:inline-block;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:700;margin-right:4px;margin-top:10px;}
.d-badge.mt{background:#EEF5FF;color:#0071E3;}
.d-badge.rp{background:#E6F4EE;color:#1D7F5F;}

/* ── Map wrapper ── */
#map-wrap{flex:1;position:relative;min-width:0;}
#map{width:100%;height:100%;}

/* Map overlays */
#status{position:absolute;top:8px;left:8px;right:52px;padding:7px 10px;border-radius:5px;
  z-index:1000;display:none;background:#FFF4F1;color:#B54708;border:1px solid #F3D5C7;
  font-size:11px;line-height:1.5;}
#status.info{background:#F0F4F8;color:#1F2937;border-color:#D6DDE5;}
#status code{font-family:ui-monospace,monospace;font-size:10px;padding:1px 4px;border-radius:3px;background:rgba(0,0,0,.06);}
#zoom-ctrl{position:absolute;top:8px;right:8px;z-index:1000;display:flex;flex-direction:column;gap:1px;}
.z-btn{width:30px;height:30px;background:#fff;border:1px solid #E4E4E0;cursor:pointer;
  font-size:17px;color:#333;display:flex;align-items:center;justify-content:center;font-weight:300;line-height:1;}
.z-btn:first-child{border-radius:4px 4px 0 0;}.z-btn:last-child{border-radius:0 0 4px 4px;}
.z-btn:hover{background:#F7F7F5;}
#legend{position:absolute;bottom:8px;right:8px;z-index:1000;background:#fff;
  border:1px solid #E4E4E0;border-radius:5px;padding:8px 10px;}
.lg-item{display:flex;align-items:center;gap:5px;font-size:10px;color:#666A70;margin-bottom:4px;}
.lg-item:last-child{margin-bottom:0;}
.lg-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;}
.lg-line{width:12px;height:3px;border-radius:1px;flex-shrink:0;}
</style>
</head>
<body>
<div id="app">
  <div id="side-panel">
    <div id="list-view">
      <div class="panel-hdr">
        <span class="panel-title">공급처 목록</span>
        <span id="sup-count" class="cnt-badge">0</span>
        <div class="filter-tabs">
          <button class="filter-tab active" id="tab-all">전체</button>
          <button class="filter-tab" id="tab-reportable">신고대상</button>
          <button class="filter-tab" id="tab-matched">매칭됨</button>
        </div>
      </div>
      <div id="stats-bar">
        일 발생량 <b id="stat-ton">-</b> 톤 ·
        신고대상 <b id="stat-reportable">-</b>건 ·
        매칭 <b id="stat-matched">-</b>건
      </div>
      <div id="sup-list"></div>
      <div id="list-footer" style="padding:8px 13px;border-top:1px solid #F0F0EE;font-size:10px;color:#888;background:#FAFAF9;flex-shrink:0;display:none;">
        목록은 일 발생량 상위 <b id="list-shown">0</b>개 표시 (총 <b id="list-total">0</b>개 마커는 지도 클릭으로 조회).
      </div>
    </div>
    <div id="detail-view">
      <div class="panel-hdr">
        <button class="back-btn" id="back-btn">← 목록으로</button>
      </div>
      <div id="detail-content"></div>
    </div>
  </div>
  <div id="map-wrap">
    <div id="map"></div>
    <div id="status"></div>
    <div id="zoom-ctrl">
      <button class="z-btn" id="btn-zi">+</button>
      <button class="z-btn" id="btn-zo">-</button>
    </div>
    <div id="legend">
      <div class="lg-item"><div class="lg-dot" style="background:#3b82f6;"></div>매칭 공급처</div>
      <div class="lg-item"><div class="lg-dot" style="background:#f59e0b;"></div>신고대상 (미매칭)</div>
      <div class="lg-item"><div class="lg-dot" style="background:#9CA3AF;"></div>일반 유출지하수</div>
      <div class="lg-item"><div class="lg-dot" style="background:#f97316;"></div>수요처</div>
      <div class="lg-item"><div class="lg-line" style="background:#22c55e;"></div>매칭 흐름</div>
    </div>
  </div>
</div>
<script>
var SUPPLIERS=__SUPPLIERS_JSON__;
var PARKS=__PARKS_JSON__;
var ROADS=__ROADS_JSON__;
var FLOWS=__FLOWS_JSON__;
var MATCHED_IDS=__MATCHED_IDS_JSON__;
var SEARCH_TERM=__SEARCH_TERM_JSON__;
var CENTER_LAT=__CENTER_LAT__;
var CENTER_LNG=__CENTER_LNG__;
var ZOOM=__ZOOM__;
var _map=null,__sdkLoaded=false,__mapReady=false,_activeItem=null,_filterMatched=false;

function __status(html,isErr){
  var s=document.getElementById('status');
  s.innerHTML=html;s.className=isErr?'':'info';s.style.display='block';
}
function __hideStatus(){document.getElementById('status').style.display='none';}
window.addEventListener('error',function(e){
  __status('❌ JS 오류: '+(e.message||'unknown')+'<br>가능 원인: Kakao 키 무효 또는 도메인 미등록.',true);
});
setTimeout(function(){
  if(__mapReady)return;
  var host=(window.location&&window.location.host)||'(iframe srcdoc)';
  if(!__sdkLoaded){
    __status('❌ Kakao SDK 로드 실패. <code>KAKAO_MAP_JS_KEY</code>가 비어있거나 네트워크 차단. iframe host: <code>'+host+'</code>',true);
  }else{
    __status('❌ SDK 로드됐지만 지도 초기화 실패.<br><b>카카오 디벨로퍼 콘솔 > Web 플랫폼</b>에 <code>'+host+'</code> 등록 누락이거나 REST API 키로 잘못 입력됨.',true);
  }
},6000);

function showList(){
  document.getElementById('list-view').style.display='flex';
  document.getElementById('list-view').style.flexDirection='column';
  document.getElementById('list-view').style.height='100%';
  document.getElementById('detail-view').style.display='none';
  if(_activeItem){_activeItem.classList.remove('active');_activeItem=null;}
}
function showDetail(html){
  document.getElementById('list-view').style.display='none';
  var dv=document.getElementById('detail-view');
  dv.style.display='flex';dv.style.flexDirection='column';dv.style.height='100%';
  document.getElementById('detail-content').innerHTML=html;
}
document.getElementById('back-btn').onclick=showList;
document.getElementById('btn-zi').onclick=function(){if(_map)_map.setLevel(_map.getLevel()-1);};
document.getElementById('btn-zo').onclick=function(){if(_map)_map.setLevel(_map.getLevel()+1);};
// Filter mode: 'all' | 'reportable' | 'matched'
var _filterMode='all';
function _passes(s){
  if(_filterMode==='matched')return !!window._matchedSet&&!!window._matchedSet[s.supplier_id];
  if(_filterMode==='reportable')return !!s.reportable;
  return true;
}
var _applyFilterRaf=0;
function _applyFilter(){
  if(!window._supItems||!window._displayedSup||!window._matchedSet)return;
  if(_applyFilterRaf)cancelAnimationFrame(_applyFilterRaf);
  _applyFilterRaf=requestAnimationFrame(function(){
    _applyFilterRaf=0;
    var cnt=0;
    var items=window._supItems;
    var disp=window._displayedSup;
    for(var i=0;i<items.length;i++){
      var show=_passes(disp[i]);
      items[i].style.display=show?'':'none';
      if(show)cnt++;
    }
    document.getElementById('sup-count').textContent=cnt;
    document.getElementById('list-shown').textContent=cnt;
    if(window._clusterers)window._clusterers.rebuild();
  });
}
function _setFilter(mode){
  _filterMode=mode;
  ['all','reportable','matched'].forEach(function(m){
    document.getElementById('tab-'+m).className='filter-tab'+(m===mode?' active':'');
  });
  _applyFilter();
  showList();
}
document.getElementById('tab-all').onclick=function(){_setFilter('all');};
document.getElementById('tab-reportable').onclick=function(){_setFilter('reportable');};
document.getElementById('tab-matched').onclick=function(){_setFilter('matched');};
</script>
<script>
// Kakao SDK에서 srcdoc iframe에서 http://t1.daumcdn.net 스크립트를 주입하는 문제:
// appendChild/insertBefore/document.write를 monkey-patch해서 http→https로 재작성.
(function(){
  function fix(node){
    if(node&&node.tagName==='SCRIPT'&&typeof node.src==='string'
        &&/^http:\/\/t1\.daumcdn\.net/.test(node.src)){
      node.src=node.src.replace(/^http:/,'https:');
    }
    return node;
  }
  var origAppend=Node.prototype.appendChild;
  Node.prototype.appendChild=function(node){return origAppend.call(this,fix(node));};
  var origInsert=Node.prototype.insertBefore;
  Node.prototype.insertBefore=function(node,ref){return origInsert.call(this,fix(node),ref);};
  var origWrite=document.write;
  document.write=function(s){
    if(typeof s==='string')s=s.replace(/http:\/\/t1\.daumcdn\.net/g,'https://t1.daumcdn.net');
    return origWrite.call(document,s);
  };
})();
</script>
<script type="text/javascript"
  src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=__JS_KEY__&autoload=false&libraries=clusterer"
  onload="__sdkLoaded=true;"
  onerror="__status('❌ Kakao SDK 스크립트 로드 실패. JS키가 비어있거나 CSP 차단.',true);"></script>
<script>
if(typeof kakao==='undefined'||!kakao.maps){}else{
kakao.maps.load(function(){
try{
var SUPPLY_SCALE=90,PARK_AREA_SCALE=200000,FLOW_TON_SCALE=30;
var container=document.getElementById('map');
_map=new kakao.maps.Map(container,{center:new kakao.maps.LatLng(CENTER_LAT,CENTER_LNG),level:ZOOM});

var matchedSet={};
MATCHED_IDS.forEach(function(id){matchedSet[id]=true;});
var supCoords={};
SUPPLIERS.forEach(function(s){supCoords[s.supplier_id]={lat:s.latitude,lng:s.longitude};});
var demCoords={};
PARKS.forEach(function(p){demCoords[p.demand_id]={lat:p.latitude,lng:p.longitude};});
ROADS.forEach(function(r){demCoords[r.demand_id]={lat:r.centroid_lat,lng:r.centroid_lng};});

// Pin (teardrop) SVG for suppliers
function pinSvg(color,w){
  var h=Math.round(w*1.55);
  var r=w*0.42;
  var cx=w/2;
  var cy=r+1.5;
  var leg=r*0.55;
  // M tip  L bottom-left  A upper-arc  Z (implicit close via bottom-right)
  var path='M '+cx+' '+h+' L '+(cx-leg)+' '+(cy+r)+' A '+r+' '+r+' 0 1 0 '+(cx+leg)+' '+(cy+r)+' Z';
  var inner='<circle cx="'+cx+'" cy="'+cy+'" r="'+(r*0.38)+'" fill="white" opacity="0.9"/>';
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="'+h+'">'
    +'<path d="'+path+'" fill="'+color+'" stroke="white" stroke-width="1.5"/>'+inner+'</svg>');
}
// Circle SVG for demand
function circSvg(color,r){
  var d=r*2;
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="'+d+'" height="'+d+'">'
    +'<circle cx="'+r+'" cy="'+r+'" r="'+(r-1.5)+'" fill="'+color+'" fill-opacity="0.85" stroke="white" stroke-width="1.5"/>'
    +'</svg>');
}
function makePinImg(color,w){
  var h=Math.round(w*1.55);
  return new kakao.maps.MarkerImage(pinSvg(color,w),new kakao.maps.Size(w,h),
    {offset:new kakao.maps.Point(w/2,h)});
}
function makeCircImg(color,r){
  return new kakao.maps.MarkerImage(circSvg(color,r),new kakao.maps.Size(r*2,r*2),
    {offset:new kakao.maps.Point(r,r)});
}

function buildSupDetail(s,matched){
  var smap={'discharging':'방류중','reported':'신고완료'};
  var status=smap[s.report_status]||s.report_status||'-';
  var badges='';
  if(matched)badges+='<span class="d-badge mt">매칭 완료</span>';
  if(s.reportable)badges+='<span class="d-badge rp">신고대상 ✓</span>';
  var geoNote=(s.geo_method==='hash_scatter')
    ?'<div style="margin-top:10px;padding:6px 8px;background:#FFF8EC;border:1px solid #F3D5C7;border-radius:4px;font-size:10px;color:#B54708;line-height:1.4;">📍 좌표 정보 미제공 자료 — 주소 해시 기반 추정 위치입니다.</div>'
    :'';
  return '<div class="d-body">'
    +'<div class="d-name">'+(s.name||'')+'</div>'
    +'<div class="d-addr">'+(s.address||'-')+'</div>'
    +'<div class="d-slbl">일 발생량</div>'
    +'<div class="d-sval">'+((s.daily_avg_supply_ton||0).toFixed(0))
    +'<span class="d-sunit"> 톤/일</span></div>'
    +'<div class="d-meta">'
    +'<div><div class="d-mlbl">수질등급</div><div class="d-mval">'+(s.water_quality_grade||'-')+'등급</div></div>'
    +'<div><div class="d-mlbl">신고상태</div><div class="d-mval">'+status+'</div></div>'
    +'</div>'
    +(badges?'<div style="margin-top:8px">'+badges+'</div>':'')
    +geoNote
    +'</div>';
}

// Aggregate stats over the FULL supplier set
var totalTon=0,totalReportable=0,totalMatched=0;
SUPPLIERS.forEach(function(s){
  totalTon+=(s.daily_avg_supply_ton||0);
  if(s.reportable)totalReportable++;
  if(matchedSet[s.supplier_id])totalMatched++;
});
document.getElementById('stat-ton').textContent=Math.round(totalTon).toLocaleString();
document.getElementById('stat-reportable').textContent=totalReportable.toLocaleString();
document.getElementById('stat-matched').textContent=totalMatched.toLocaleString();

// Sort by ton desc; side panel limits to top N for DOM perf
var sortedSup=SUPPLIERS.slice().sort(function(a,b){
  return (b.daily_avg_supply_ton||0)-(a.daily_avg_supply_ton||0);
});
var SIDE_LIMIT=__SIDE_PANEL_LIMIT__;
var displayedSup=sortedSup.slice(0,SIDE_LIMIT);
window._displayedSup=displayedSup;window._matchedSet=matchedSet;
document.getElementById('sup-count').textContent=displayedSup.length;
if(sortedSup.length>SIDE_LIMIT){
  document.getElementById('list-footer').style.display='block';
  document.getElementById('list-total').textContent=sortedSup.length.toLocaleString();
  document.getElementById('list-shown').textContent=displayedSup.length.toLocaleString();
}

var supListEl=document.getElementById('sup-list');
var supItems=[];
displayedSup.forEach(function(s,idx){
  var matched=!!matchedSet[s.supplier_id];
  var rankCls=matched?'m':(s.reportable?'u':'u');
  var item=document.createElement('div');
  item.className='sup-item';
  item.innerHTML='<div class="sup-rank '+rankCls+'">'+(idx+1)+'</div>'
    +'<div class="sup-info">'
    +'<div class="sup-name">'+(s.name||'')+'</div>'
    +'<div class="sup-ton">'+((s.daily_avg_supply_ton||0).toFixed(0))+' 톤/일'
      +(s.reportable?' · <span style="color:#B54708">신고대상</span>':'')
    +'</div>'
    +'<div class="sup-addr">'+(s.address||'')+'</div>'
    +'</div>';
  (function(s,matched,item){
    item.onclick=function(){
      if(_activeItem)_activeItem.classList.remove('active');
      _activeItem=item;item.classList.add('active');
      _map.setCenter(new kakao.maps.LatLng(s.latitude,s.longitude));
      _map.setLevel(4);
      showDetail(buildSupDetail(s,matched));
    };
  })(s,matched,item);
  supListEl.appendChild(item);
  supItems.push(item);
});
window._supItems=supItems;

// Shared marker images keyed by category — huge perf win vs per-marker SVG
var imgMatched=makePinImg('#3b82f6',20);
var imgReportable=makePinImg('#f59e0b',18);
var imgRegular=makeCircImg('#9CA3AF',6);

// Build every supplier marker; clusterer manages visibility per zoom
var markersAll=[],markersReportable=[],markersMatched=[];
SUPPLIERS.forEach(function(s){
  var matched=!!matchedSet[s.supplier_id];
  var img=matched?imgMatched:(s.reportable?imgReportable:imgRegular);
  var marker=new kakao.maps.Marker({
    position:new kakao.maps.LatLng(s.latitude,s.longitude),
    image:img,
    title:s.name||''
  });
  (function(s,matched){
    kakao.maps.event.addListener(marker,'click',function(){
      _map.setCenter(new kakao.maps.LatLng(s.latitude,s.longitude));
      showDetail(buildSupDetail(s,matched));
    });
  })(s,matched);
  markersAll.push(marker);
  if(s.reportable)markersReportable.push(marker);
  if(matched)markersMatched.push(marker);
});

var clusterer=new kakao.maps.MarkerClusterer({
  map:_map,
  averageCenter:true,
  minLevel:5,
  gridSize:60,
  disableClickZoom:false,
  styles:[{
    width:'34px',height:'34px',background:'rgba(29,127,95,0.85)',color:'#fff',
    borderRadius:'17px',textAlign:'center',lineHeight:'34px',fontSize:'12px',fontWeight:'700'
  }]
});
clusterer.addMarkers(markersAll);
window._clusterers={
  rebuild:function(){
    var pool=markersAll;
    if(_filterMode==='reportable')pool=markersReportable;
    else if(_filterMode==='matched')pool=markersMatched;
    clusterer.clear();
    clusterer.addMarkers(pool);
  }
};
_applyFilter();

// Demand markers tracked for viewport culling on idle
var parkMarkers=[];
PARKS.forEach(function(p){
  var r=Math.max(5,Math.min(14,Math.round((p.area_m2||100000)/PARK_AREA_SCALE*14)));
  var marker=new kakao.maps.Marker({
    map:_map,
    position:new kakao.maps.LatLng(p.latitude,p.longitude),
    image:makeCircImg('#f97316',r),
    title:p.name||''
  });
  marker._lat=p.latitude;marker._lng=p.longitude;
  (function(p){
    kakao.maps.event.addListener(marker,'click',function(){
      showDetail('<div class="d-body"><div class="d-name">'+(p.name||'')+'</div>'
        +'<div class="d-addr">공원</div>'
        +'<div class="d-slbl" style="margin-top:12px">면적</div>'
        +'<div class="d-sval">'+((p.area_m2||0).toLocaleString())
        +'<span class="d-sunit"> m\u00b2</span></div></div>');
    });
  })(p);
  parkMarkers.push(marker);
});

var roadMarkers=[];
ROADS.forEach(function(r){
  var marker=new kakao.maps.Marker({
    map:_map,
    position:new kakao.maps.LatLng(r.centroid_lat,r.centroid_lng),
    image:makeCircImg('#fb923c',5),
    title:r.name||''
  });
  marker._lat=r.centroid_lat;marker._lng=r.centroid_lng;
  (function(r){
    kakao.maps.event.addListener(marker,'click',function(){
      showDetail('<div class="d-body"><div class="d-name">'+(r.name||'')+'</div>'
        +'<div class="d-addr">도로</div>'
        +'<div class="d-slbl" style="margin-top:12px">연장</div>'
        +'<div class="d-sval">'+((r.length_m||0).toFixed(0))
        +'<span class="d-sunit"> m</span></div></div>');
    });
  })(r);
  roadMarkers.push(marker);
});

// Flow polylines — tracked for level/bounds-aware visibility
var flowLines=[];
FLOWS.forEach(function(f){
  var sc=supCoords[f.supplier_id];
  var dc=demCoords[f.demand_id];
  if(!sc||!dc)return;
  var line=new kakao.maps.Polyline({
    map:_map,
    path:[new kakao.maps.LatLng(sc.lat,sc.lng),new kakao.maps.LatLng(dc.lat,dc.lng)],
    strokeWeight:Math.max(2,Math.min(7,(f.ton_per_day||10)/FLOW_TON_SCALE)),
    strokeColor:'#22c55e',strokeOpacity:0.65,strokeStyle:'solid'
  });
  line._sLat=sc.lat;line._sLng=sc.lng;line._dLat=dc.lat;line._dLng=dc.lng;
  flowLines.push(line);
});

// Viewport culling on idle: keep DOM low while panning at city scale.
// Suppliers go through MarkerClusterer; we cull parks/roads/flows.
var FLOW_HIDE_LEVEL=__FLOW_HIDE_LEVEL__;
var _idleTimer=0;
function _withinBounds(b,lat,lng){
  var sw=b.getSouthWest(),ne=b.getNorthEast();
  return lat>=sw.getLat()&&lat<=ne.getLat()&&lng>=sw.getLng()&&lng<=ne.getLng();
}
function _cullDemand(){
  var bounds=_map.getBounds();
  var level=_map.getLevel();
  for(var i=0;i<parkMarkers.length;i++){
    var m=parkMarkers[i];
    var show=_withinBounds(bounds,m._lat,m._lng);
    if(show&&!m.getMap())m.setMap(_map);
    else if(!show&&m.getMap())m.setMap(null);
  }
  for(var j=0;j<roadMarkers.length;j++){
    var rm=roadMarkers[j];
    var show2=_withinBounds(bounds,rm._lat,rm._lng);
    if(show2&&!rm.getMap())rm.setMap(_map);
    else if(!show2&&rm.getMap())rm.setMap(null);
  }
  var hideFlows=level>=FLOW_HIDE_LEVEL;
  for(var k=0;k<flowLines.length;k++){
    var fl=flowLines[k];
    var inView=!hideFlows&&(_withinBounds(bounds,fl._sLat,fl._sLng)||_withinBounds(bounds,fl._dLat,fl._dLng));
    if(inView&&!fl.getMap())fl.setMap(_map);
    else if(!inView&&fl.getMap())fl.setMap(null);
  }
}
function _scheduleCull(){
  if(_idleTimer)clearTimeout(_idleTimer);
  _idleTimer=setTimeout(function(){_idleTimer=0;_cullDemand();},__IDLE_THROTTLE_MS__);
}
kakao.maps.event.addListener(_map,'idle',_scheduleCull);
_cullDemand();

// Search: zoom to match + show detail in panel (lower-cased name cache built once)
var nameLower=new Array(sortedSup.length);
for(var ni=0;ni<sortedSup.length;ni++){
  nameLower[ni]=(sortedSup[ni].name||'').toLowerCase();
}
if(SEARCH_TERM){
  var term=SEARCH_TERM.toLowerCase();
  for(var i=0;i<sortedSup.length;i++){
    if(nameLower[i].indexOf(term)>=0){
      var sd=sortedSup[i];
      var matched2=!!matchedSet[sd.supplier_id];
      _map.setCenter(new kakao.maps.LatLng(sd.latitude,sd.longitude));
      _map.setLevel(4);
      if(i<supItems.length){
        var it=supItems[i];
        if(it){if(_activeItem)_activeItem.classList.remove('active');_activeItem=it;it.classList.add('active');
        it.scrollIntoView({block:'nearest'});}
      }
      showDetail(buildSupDetail(sd,matched2));
      break;
    }
  }
}

__mapReady=true;
__hideStatus();
}catch(e){__status('❌ 지도 초기화 오류: '+(e&&e.message?e.message:e),true);}
});}
</script>
</body>
</html>"""


@st.cache_data(show_spinner=False, max_entries=16)
def build_kakao_map_html(
    suppliers: pd.DataFrame,
    parks: pd.DataFrame,
    roads: pd.DataFrame,
    flows: pd.DataFrame,
    search_term: str,
    js_key: str,
) -> str:
    """Build an HTML string embedding the Naver-style Kakao Maps UI.

    Cached per (suppliers, parks, roads, flows, search_term, js_key) tuple so that
    Streamlit reruns triggered by unrelated widget state do not re-serialize data
    or re-build the iframe HTML.

    Returns:
        HTML string suitable for st.components.v1.html().
    """
    matched_ids: set[str] = (
        set(flows["supplier_id"].astype(str).tolist()) if not flows.empty else set()
    )
    center_lat, center_lng, zoom = _compute_center(suppliers, search_term)
    return (
        _HTML_TEMPLATE.replace("__JS_KEY__", js_key)
        .replace("__CENTER_LAT__", str(center_lat))
        .replace("__CENTER_LNG__", str(center_lng))
        .replace("__ZOOM__", str(zoom))
        .replace("__SIDE_PANEL_LIMIT__", str(_SIDE_PANEL_LIMIT))
        .replace("__SUPPLIERS_JSON__", _df_to_json(suppliers, _SUPPLIER_COLS))
        .replace("__PARKS_JSON__", _df_to_json(parks, _PARK_COLS))
        .replace("__ROADS_JSON__", _df_to_json(roads, _ROAD_COLS))
        .replace("__FLOWS_JSON__", _df_to_json(flows, _FLOW_COLS))
        .replace("__MATCHED_IDS_JSON__", json.dumps(list(matched_ids), ensure_ascii=False))
        .replace("__SEARCH_TERM_JSON__", json.dumps(search_term, ensure_ascii=False))
        .replace("__FLOW_HIDE_LEVEL__", str(_JS_FLOW_HIDE_LEVEL))
        .replace("__IDLE_THROTTLE_MS__", str(_JS_IDLE_THROTTLE_MS))
    )


def _compute_center(suppliers: pd.DataFrame, search_term: str) -> tuple[float, float, int]:
    if not search_term or suppliers.empty or "name" not in suppliers.columns:
        return SEOUL_LAT, SEOUL_LNG, DEFAULT_ZOOM
    term = search_term.lower()
    mask = suppliers["name"].astype(str).str.lower().str.contains(term, regex=False, na=False)
    matched = suppliers.loc[mask]
    if matched.empty or "latitude" not in matched.columns or "longitude" not in matched.columns:
        return SEOUL_LAT, SEOUL_LNG, DEFAULT_ZOOM
    lat: float = float(matched["latitude"].iloc[0])
    lng: float = float(matched["longitude"].iloc[0])
    if math.isfinite(lat) and math.isfinite(lng):
        return lat, lng, SEARCH_ZOOM
    return SEOUL_LAT, SEOUL_LNG, DEFAULT_ZOOM


def _df_to_json(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "[]"
    available = [c for c in columns if c in df.columns]
    subset: pd.DataFrame = df.filter(items=available, axis="columns").reset_index(drop=True)
    records: list[dict[str, object]] = []
    for idx in range(len(subset)):
        clean: dict[str, object] = {}
        for col in available:
            raw: object = subset.loc[idx, col]
            if isinstance(raw, np.generic):
                raw = raw.item()
            v: object
            if isinstance(raw, float) and not math.isfinite(raw):
                v = None
            elif hasattr(raw, "isoformat"):
                v = str(raw)
            else:
                v = raw
            clean[col] = v
        records.append(clean)
    return json.dumps(records, ensure_ascii=False)
