from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING

import numpy as np

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

_SUPPLIER_COLS: list[str] = [
    "supplier_id",
    "name",
    "address",
    "latitude",
    "longitude",
    "daily_avg_supply_ton",
    "water_quality_grade",
    "report_status",
]
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
          <button class="filter-tab" id="tab-matched">매칭됨</button>
        </div>
      </div>
      <div id="sup-list"></div>
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
      <div class="lg-item"><div class="lg-dot" style="background:#ef4444;"></div>미매칭 공급처</div>
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
// Filter tabs — wired after kakao.maps.load builds supItems
function _applyFilter(){
  // Called after supItems is built; no-op before that
  if(!window._supItems||!window._sortedSup||!window._matchedSet)return;
  var cnt=0;
  window._supItems.forEach(function(item,idx){
    var s=window._sortedSup[idx];
    var show=!_filterMatched||!!window._matchedSet[s.supplier_id];
    item.style.display=show?'':'none';
    if(show)cnt++;
  });
  document.getElementById('sup-count').textContent=cnt;
}
function _setFilter(matched){
  _filterMatched=matched;
  document.getElementById('tab-all').className='filter-tab'+(matched?'':' active');
  document.getElementById('tab-matched').className='filter-tab'+(matched?' active':'');
  _applyFilter();
  showList();
}
document.getElementById('tab-all').onclick=function(){_setFilter(false);};
document.getElementById('tab-matched').onclick=function(){_setFilter(true);};
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
  src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=__JS_KEY__&autoload=false"
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
  if(s.report_status==='reported')badges+='<span class="d-badge rp">신고대상 ✓</span>';
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
    +'</div>';
}

// Sort suppliers by ton/day descending for list
var sortedSup=SUPPLIERS.slice().sort(function(a,b){
  return (b.daily_avg_supply_ton||0)-(a.daily_avg_supply_ton||0);
});
window._sortedSup=sortedSup;window._matchedSet=matchedSet;
var supItems=[];
var supListEl=document.getElementById('sup-list');
document.getElementById('sup-count').textContent=sortedSup.length;

// Lookup: supplier_id -> index in sortedSup
var supIdxMap={};
sortedSup.forEach(function(s,i){supIdxMap[s.supplier_id]=i;});

// Build list DOM
sortedSup.forEach(function(s,idx){
  var matched=!!matchedSet[s.supplier_id];
  var item=document.createElement('div');
  item.className='sup-item';
  item.innerHTML='<div class="sup-rank '+(matched?'m':'u')+'">'+(idx+1)+'</div>'
    +'<div class="sup-info">'
    +'<div class="sup-name">'+(s.name||'')+'</div>'
    +'<div class="sup-ton">'+((s.daily_avg_supply_ton||0).toFixed(0))+' 톤/일</div>'
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
_applyFilter();

// Build supplier markers (pin style)
SUPPLIERS.forEach(function(s){
  var matched=!!matchedSet[s.supplier_id];
  var color=matched?'#3b82f6':'#ef4444';
  var w=Math.max(14,Math.min(28,Math.round(10+(s.daily_avg_supply_ton||100)/SUPPLY_SCALE*14)));
  var marker=new kakao.maps.Marker({
    map:_map,
    position:new kakao.maps.LatLng(s.latitude,s.longitude),
    image:makePinImg(color,w),
    title:s.name||''
  });
  var listIdx=supIdxMap[s.supplier_id];
  var item_el=(listIdx!==undefined)?supItems[listIdx]:null;
  (function(s,matched,item_el){
    kakao.maps.event.addListener(marker,'click',function(){
      _map.setCenter(new kakao.maps.LatLng(s.latitude,s.longitude));
      if(item_el){
        if(_activeItem)_activeItem.classList.remove('active');
        _activeItem=item_el;item_el.classList.add('active');
        item_el.scrollIntoView({block:'nearest'});
      }
      showDetail(buildSupDetail(s,matched));
    });
  })(s,matched,item_el);
});

// Park markers (circle)
PARKS.forEach(function(p){
  var r=Math.max(5,Math.min(14,Math.round((p.area_m2||100000)/PARK_AREA_SCALE*14)));
  var marker=new kakao.maps.Marker({
    map:_map,
    position:new kakao.maps.LatLng(p.latitude,p.longitude),
    image:makeCircImg('#f97316',r),
    title:p.name||''
  });
  (function(p){
    kakao.maps.event.addListener(marker,'click',function(){
      showDetail('<div class="d-body"><div class="d-name">'+(p.name||'')+'</div>'
        +'<div class="d-addr">공원</div>'
        +'<div class="d-slbl" style="margin-top:12px">면적</div>'
        +'<div class="d-sval">'+((p.area_m2||0).toLocaleString())
        +'<span class="d-sunit"> m\u00b2</span></div></div>');
    });
  })(p);
});

// Road markers (small circle)
ROADS.forEach(function(r){
  var marker=new kakao.maps.Marker({
    map:_map,
    position:new kakao.maps.LatLng(r.centroid_lat,r.centroid_lng),
    image:makeCircImg('#fb923c',5),
    title:r.name||''
  });
  (function(r){
    kakao.maps.event.addListener(marker,'click',function(){
      showDetail('<div class="d-body"><div class="d-name">'+(r.name||'')+'</div>'
        +'<div class="d-addr">도로</div>'
        +'<div class="d-slbl" style="margin-top:12px">연장</div>'
        +'<div class="d-sval">'+((r.length_m||0).toFixed(0))
        +'<span class="d-sunit"> m</span></div></div>');
    });
  })(r);
});

// Flow polylines
FLOWS.forEach(function(f){
  var sc=supCoords[f.supplier_id];
  var dc=demCoords[f.demand_id];
  if(!sc||!dc)return;
  new kakao.maps.Polyline({
    map:_map,
    path:[new kakao.maps.LatLng(sc.lat,sc.lng),new kakao.maps.LatLng(dc.lat,dc.lng)],
    strokeWeight:Math.max(2,Math.min(7,(f.ton_per_day||10)/FLOW_TON_SCALE)),
    strokeColor:'#22c55e',strokeOpacity:0.65,strokeStyle:'solid'
  });
});

// Search: zoom to match + show detail in panel
if(SEARCH_TERM){
  var term=SEARCH_TERM.toLowerCase();
  for(var i=0;i<sortedSup.length;i++){
    var nm=(sortedSup[i].name||'').toLowerCase();
    if(nm.indexOf(term)>=0){
      var sd=sortedSup[i];
      var matched2=!!matchedSet[sd.supplier_id];
      _map.setCenter(new kakao.maps.LatLng(sd.latitude,sd.longitude));
      _map.setLevel(4);
      var it=supItems[i];
      if(it){if(_activeItem)_activeItem.classList.remove('active');_activeItem=it;it.classList.add('active');}
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


def build_kakao_map_html(
    suppliers: pd.DataFrame,
    parks: pd.DataFrame,
    roads: pd.DataFrame,
    flows: pd.DataFrame,
    search_term: str,
    js_key: str,
) -> str:
    """Build an HTML string embedding the Naver-style Kakao Maps UI.

    Returns:
        HTML string suitable for st.components.v1.html().
    """
    if "reportable" in suppliers.columns:
        suppliers = suppliers.loc[suppliers["reportable"].astype(bool)]
    matched_ids: set[str] = (
        set(flows["supplier_id"].astype(str).tolist()) if not flows.empty else set()
    )
    center_lat, center_lng, zoom = _compute_center(suppliers, search_term)
    return (
        _HTML_TEMPLATE.replace("__JS_KEY__", js_key)
        .replace("__CENTER_LAT__", str(center_lat))
        .replace("__CENTER_LNG__", str(center_lng))
        .replace("__ZOOM__", str(zoom))
        .replace("__SUPPLIERS_JSON__", _df_to_json(suppliers, _SUPPLIER_COLS))
        .replace("__PARKS_JSON__", _df_to_json(parks, _PARK_COLS))
        .replace("__ROADS_JSON__", _df_to_json(roads, _ROAD_COLS))
        .replace("__FLOWS_JSON__", _df_to_json(flows, _FLOW_COLS))
        .replace("__MATCHED_IDS_JSON__", json.dumps(list(matched_ids), ensure_ascii=False))
        .replace("__SEARCH_TERM_JSON__", json.dumps(search_term, ensure_ascii=False))
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
