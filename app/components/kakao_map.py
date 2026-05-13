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
MAX_SUPPLY_RADIUS: float = 24.0
MIN_SUPPLY_RADIUS: float = 10.0
SUPPLY_SCALE: float = 90.0
MAX_PARK_RADIUS: float = 16.0
MIN_PARK_RADIUS: float = 6.0
PARK_AREA_SCALE: float = 180_000.0
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

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
html,body{margin:0;padding:0;height:100%;}
#map{width:100%;height:100%;}
#status{position:absolute;top:10px;left:10px;right:10px;padding:8px 12px;border-radius:6px;
font:12px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;
z-index:1000;display:none;background:#FFF4F1;color:#B54708;border:1px solid #F3D5C7;}
#status.info{background:#F0F4F8;color:#1F2937;border-color:#D6DDE5;}
#status code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
padding:1px 4px;border-radius:3px;background:rgba(0,0,0,0.06);}
</style>
</head>
<body>
<div id="map"></div>
<div id="status"></div>
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
var __sdkLoaded=false,__mapReady=false;
function __status(html,isError){
  var s=document.getElementById('status');
  s.innerHTML=html;
  s.className=isError?'':'info';
  s.style.display='block';
}
function __hideStatus(){document.getElementById('status').style.display='none';}
window.addEventListener('error',function(e){
  __status('❌ JS 오류: '+(e.message||'unknown')+'<br>가능 원인: Kakao 키 무효 또는 도메인 미등록.',true);
});
setTimeout(function(){
  if(__mapReady)return;
  var host=(window.location&&window.location.host)||'(iframe srcdoc)';
  if(!__sdkLoaded){
    __status('❌ Kakao SDK 스크립트 로드 실패. <code>KAKAO_MAP_JS_KEY</code>가 비어있거나 네트워크 차단. iframe host: <code>'+host+'</code>',true);
  } else {
    __status('❌ SDK는 로드됐지만 지도가 초기화되지 않았습니다.<br>대부분 <b>카카오 디벨로퍼 콘솔 > 플랫폼 > Web</b>에 <code>'+host+'</code> 등록 누락. 또는 키가 <b>REST API 키</b>로 잘못 입력됨 (JavaScript 키 필요).',true);
  }
},6000);
</script>
<script>
// Streamlit components.html iframe은 srcdoc 컨텍스트라서 window.location.protocol
// 이 'about:'. dapi.kakao.com 로더는 이를 보고 nested kakao.js를 http:// 로
// 요청 → HTTPS 페이지에서 mixed-content 차단됨.
// 해결: appendChild·insertBefore·document.write를 monkey-patch해서 로더가
// 주입하는 http://t1.daumcdn.net 스크립트를 https:// 로 재작성.
// 로더는 그대로 두어 kakao.maps 네임스페이스(특히 kakao.maps.load) 셋업은 정상 진행.
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
  onerror="__status('❌ Kakao SDK 스크립트 자체가 로드 실패. JS키가 비어있거나 CSP 차단.',true);"></script>
<script>
if(typeof kakao==='undefined'||!kakao.maps){
  // SDK 미정의 — onerror 또는 timeout 핸들러가 처리
} else { kakao.maps.load(function(){
try {
var container=document.getElementById('map');
var map=new kakao.maps.Map(container,{center:new kakao.maps.LatLng(CENTER_LAT,CENTER_LNG),level:ZOOM});
var infowindow=new kakao.maps.InfoWindow({zIndex:1});
var matchedSet={};
MATCHED_IDS.forEach(function(id){matchedSet[id]=true;});
var supCoords={};
SUPPLIERS.forEach(function(s){supCoords[s.supplier_id]={lat:s.latitude,lng:s.longitude};});
var demCoords={};
PARKS.forEach(function(p){demCoords[p.demand_id]={lat:p.latitude,lng:p.longitude};});
ROADS.forEach(function(r){demCoords[r.demand_id]={lat:r.centroid_lat,lng:r.centroid_lng};});

function svgSrc(color,r){
var d=r*2;
var svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+d+'" height="'+d+'"><circle cx="'+r+'" cy="'+r+'" r="'+(r-2)+'" fill="'+color+'" fill-opacity="0.82" stroke="white" stroke-width="2"/></svg>';
return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function makeImg(color,r){return new kakao.maps.MarkerImage(svgSrc(color,r),new kakao.maps.Size(r*2,r*2),{offset:new kakao.maps.Point(r,r)});}

var supMarkers=[];
SUPPLIERS.forEach(function(s){
var matched=!!matchedSet[s.supplier_id];
var color=matched?'#3b82f6':'#ef4444';
var r=Math.max(10,Math.min(24,(s.daily_avg_supply_ton||100)/90));
var marker=new kakao.maps.Marker({map:map,position:new kakao.maps.LatLng(s.latitude,s.longitude),image:makeImg(color,r),title:s.name||''});
var html='<div style="padding:6px 10px;font-size:12px;line-height:1.7;min-width:160px;">'
+'<b>'+(s.name||'')+'</b><br>'
+'발생량: '+((s.daily_avg_supply_ton||0).toFixed(0))+' 톤/일<br>'
+'수질등급: '+(s.water_quality_grade||'-')+'등급<br>'
+'신고상태: '+(s.report_status||'-')
+'</div>';
(function(m,h){kakao.maps.event.addListener(m,'click',function(){infowindow.setContent(h);infowindow.open(map,m);});})(marker,html);
supMarkers.push({marker:marker,data:s});
});

PARKS.forEach(function(p){
var r=Math.max(6,Math.min(16,(p.area_m2||100000)/180000));
var marker=new kakao.maps.Marker({map:map,position:new kakao.maps.LatLng(p.latitude,p.longitude),image:makeImg('#f97316',r),title:p.name||''});
var html='<div style="padding:6px 10px;font-size:12px;line-height:1.7;">'+'<b>'+(p.name||'')+'</b> (공원)<br>'+((p.area_m2||0).toLocaleString())+' m\u00b2'+'</div>';
(function(m,h){kakao.maps.event.addListener(m,'click',function(){infowindow.setContent(h);infowindow.open(map,m);});})(marker,html);
});

ROADS.forEach(function(r){
var marker=new kakao.maps.Marker({map:map,position:new kakao.maps.LatLng(r.centroid_lat,r.centroid_lng),image:makeImg('#fb923c',6),title:r.name||''});
var html='<div style="padding:6px 10px;font-size:12px;line-height:1.7;">'+'<b>'+(r.name||'')+'</b> (도로)<br>'+((r.length_m||0).toFixed(0))+' m'+'</div>';
(function(m,h){kakao.maps.event.addListener(m,'click',function(){infowindow.setContent(h);infowindow.open(map,m);});})(marker,html);
});

FLOWS.forEach(function(f){
var sc=supCoords[f.supplier_id];
var dc=demCoords[f.demand_id];
if(!sc||!dc)return;
new kakao.maps.Polyline({map:map,path:[new kakao.maps.LatLng(sc.lat,sc.lng),new kakao.maps.LatLng(dc.lat,dc.lng)],strokeWeight:Math.max(2,Math.min(7,(f.ton_per_day||10)/30)),strokeColor:'#22c55e',strokeOpacity:0.65,strokeStyle:'solid'});
});

if(SEARCH_TERM){
var term=SEARCH_TERM.toLowerCase();
for(var i=0;i<supMarkers.length;i++){
var nm=(supMarkers[i].data.name||'').toLowerCase();
if(nm.indexOf(term)>=0){
var sd=supMarkers[i].data;
map.setCenter(new kakao.maps.LatLng(sd.latitude,sd.longitude));
map.setLevel(4);
var sh='<div style="padding:6px 10px;font-size:12px;line-height:1.7;min-width:160px;">'
+'<b>'+(sd.name||'')+'</b><br>'
+'발생량: '+((sd.daily_avg_supply_ton||0).toFixed(0))+' 톤/일<br>'
+'수질등급: '+(sd.water_quality_grade||'-')+'등급<br>'
+'신고상태: '+(sd.report_status||'-')
+'</div>';
infowindow.setContent(sh);
infowindow.open(map,supMarkers[i].marker);
break;
}
}
}
__mapReady=true;
__hideStatus();
} catch(e) {
  __status('❌ 지도 초기화 오류: '+(e&&e.message?e.message:e),true);
}
}); }
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
    """Build an HTML string embedding Kakao Maps for the matching visualization.

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
