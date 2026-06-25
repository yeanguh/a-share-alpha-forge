from __future__ import annotations

import json
from pathlib import Path

import cairosvg


OUT_DIR = Path(__file__).resolve().parent
ASSET_DIR = OUT_DIR / "assets"


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1880" width="1400" height="1880">
<style>
text { font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Heiti SC', Arial, sans-serif; fill: #111827; }
.title { font-size: 34px; font-weight: 700; }
.subtitle { font-size: 18px; fill: #4b5563; }
.layer { font-size: 22px; font-weight: 700; }
.node-title { font-size: 19px; font-weight: 700; }
.node-sub { font-size: 14px; fill: #4b5563; }
.small { font-size: 13px; fill: #6b7280; }
.box { fill: #ffffff; stroke: #d1d5db; stroke-width: 2; rx: 10; ry: 10; }
.blue { fill: #eff6ff; stroke: #bfdbfe; }
.green { fill: #f0fdf4; stroke: #bbf7d0; }
.purple { fill: #faf5ff; stroke: #e9d5ff; }
.orange { fill: #fff7ed; stroke: #fed7aa; }
.red { fill: #fef2f2; stroke: #fecaca; }
.side { fill: #ffffff; stroke: #c4b5fd; stroke-width: 2; stroke-dasharray: 8 6; rx: 10; ry: 10; }
.commodity { fill: #ffffff; stroke: #fbbf24; stroke-width: 2; stroke-dasharray: 8 6; rx: 10; ry: 10; }
</style>
<defs>
  <marker id="arrow-blue" markerWidth="12" markerHeight="9" refX="11" refY="4.5" orient="auto"><polygon points="0 0, 12 4.5, 0 9" fill="#2563eb"/></marker>
  <marker id="arrow-green" markerWidth="12" markerHeight="9" refX="11" refY="4.5" orient="auto"><polygon points="0 0, 12 4.5, 0 9" fill="#16a34a"/></marker>
  <marker id="arrow-purple" markerWidth="12" markerHeight="9" refX="11" refY="4.5" orient="auto"><polygon points="0 0, 12 4.5, 0 9" fill="#9333ea"/></marker>
  <marker id="arrow-red" markerWidth="12" markerHeight="9" refX="11" refY="4.5" orient="auto"><polygon points="0 0, 12 4.5, 0 9" fill="#dc2626"/></marker>
</defs>
<rect width="1400" height="1880" fill="#ffffff"/>
<text x="700" y="56" text-anchor="middle" class="title">液冷服务器产业链全景图谱</text>
<text x="700" y="88" text-anchor="middle" class="subtitle">AI机架功耗密度提升：冷板/浸没/喷淋路线，连接CDU、冷板、管路、冷却液、测试与运维</text>

<rect x="80" y="130" width="840" height="290" class="blue box"/>
<text x="110" y="168" class="layer">上游资源、材料与关键部件</text>
<rect x="120" y="195" width="230" height="82" class="green box"/>
<text x="235" y="224" text-anchor="middle" class="node-title">金属与结构件</text>
<text x="235" y="249" text-anchor="middle" class="node-sub">铜/铝/不锈钢、钎焊、机加工</text>
<text x="235" y="270" text-anchor="middle" class="node-sub">冷板、歧管、快接头</text>
<rect x="390" y="195" width="230" height="82" class="green box"/>
<text x="505" y="224" text-anchor="middle" class="node-title">泵阀与传感器</text>
<text x="505" y="249" text-anchor="middle" class="node-sub">泵、阀、流量/压力/泄漏监测</text>
<text x="505" y="270" text-anchor="middle" class="node-sub">可靠性与冗余设计</text>
<rect x="660" y="195" width="220" height="82" class="green box"/>
<text x="770" y="224" text-anchor="middle" class="node-title">冷却液与化学品</text>
<text x="770" y="249" text-anchor="middle" class="node-sub">乙二醇/去离子水/氟化液</text>
<text x="770" y="270" text-anchor="middle" class="node-sub">缓蚀、绝缘、低挥发</text>
<rect x="120" y="305" width="230" height="82" class="orange box"/>
<text x="235" y="334" text-anchor="middle" class="node-title">导热与密封材料</text>
<text x="235" y="359" text-anchor="middle" class="node-sub">TIM、垫片、O形圈、软管</text>
<text x="235" y="380" text-anchor="middle" class="node-sub">EPDM/FKM/PTFE/PPS</text>
<rect x="390" y="305" width="230" height="82" class="orange box"/>
<text x="505" y="334" text-anchor="middle" class="node-title">换热器与风液复合</text>
<text x="505" y="359" text-anchor="middle" class="node-sub">干冷器、冷却塔、板换</text>
<text x="505" y="380" text-anchor="middle" class="node-sub">自然冷却与余热回收</text>
<rect x="660" y="305" width="220" height="82" class="orange box"/>
<text x="770" y="334" text-anchor="middle" class="node-title">检测与施工耗材</text>
<text x="770" y="359" text-anchor="middle" class="node-sub">气密/质谱检漏、过滤、补液</text>
<text x="770" y="380" text-anchor="middle" class="node-sub">安装调试、运维备件</text>

<rect x="80" y="505" width="840" height="305" class="blue box"/>
<text x="110" y="543" class="layer">中游液冷系统集成</text>
<rect x="120" y="575" width="230" height="82" class="blue box"/>
<text x="235" y="604" text-anchor="middle" class="node-title">冷板式液冷</text>
<text x="235" y="629" text-anchor="middle" class="node-sub">GPU/CPU冷板 + 机柜管路</text>
<text x="235" y="650" text-anchor="middle" class="node-sub">当前AI服务器主线</text>
<rect x="390" y="575" width="230" height="82" class="blue box"/>
<text x="505" y="604" text-anchor="middle" class="node-title">CDU与二次侧</text>
<text x="505" y="629" text-anchor="middle" class="node-sub">泵、板换、控制、冗余</text>
<text x="505" y="650" text-anchor="middle" class="node-sub">连接机柜与冷源</text>
<rect x="660" y="575" width="220" height="82" class="blue box"/>
<text x="770" y="604" text-anchor="middle" class="node-title">浸没/喷淋路线</text>
<text x="770" y="629" text-anchor="middle" class="node-sub">更高热流密度场景</text>
<text x="770" y="650" text-anchor="middle" class="node-sub">冷却液成本与兼容性敏感</text>
<rect x="120" y="685" width="230" height="82" class="purple box"/>
<text x="235" y="714" text-anchor="middle" class="node-title">机柜与Manifold</text>
<text x="235" y="739" text-anchor="middle" class="node-sub">快接、盲插、漏液隔离</text>
<text x="235" y="760" text-anchor="middle" class="node-sub">标准化交付能力</text>
<rect x="390" y="685" width="230" height="82" class="purple box"/>
<text x="505" y="714" text-anchor="middle" class="node-title">控制软件与监控</text>
<text x="505" y="739" text-anchor="middle" class="node-sub">温度/流量/压差闭环</text>
<text x="505" y="760" text-anchor="middle" class="node-sub">故障预警、能效优化</text>
<rect x="660" y="685" width="220" height="82" class="purple box"/>
<text x="770" y="714" text-anchor="middle" class="node-title">测试认证与交付</text>
<text x="770" y="739" text-anchor="middle" class="node-sub">气密、热循环、腐蚀、振动</text>
<text x="770" y="760" text-anchor="middle" class="node-sub">客户验证周期是壁垒</text>

<rect x="80" y="890" width="840" height="275" class="blue box"/>
<text x="110" y="928" class="layer">下游服务器、机房与运营</text>
<rect x="120" y="960" width="230" height="82" class="green box"/>
<text x="235" y="989" text-anchor="middle" class="node-title">AI服务器/整机厂</text>
<text x="235" y="1014" text-anchor="middle" class="node-sub">GPU服务器、NVL机架</text>
<text x="235" y="1035" text-anchor="middle" class="node-sub">液冷设计前置绑定</text>
<rect x="390" y="960" width="230" height="82" class="green box"/>
<text x="505" y="989" text-anchor="middle" class="node-title">AIDC/云厂商</text>
<text x="505" y="1014" text-anchor="middle" class="node-sub">算力集群采购与运维</text>
<text x="505" y="1035" text-anchor="middle" class="node-sub">PUE与机架功率约束</text>
<rect x="660" y="960" width="220" height="82" class="green box"/>
<text x="770" y="989" text-anchor="middle" class="node-title">机房工程与运维</text>
<text x="770" y="1014" text-anchor="middle" class="node-sub">管网、冷源、消防、补液</text>
<text x="770" y="1035" text-anchor="middle" class="node-sub">从设备销售到服务收入</text>
<rect x="255" y="1070" width="230" height="62" class="orange box"/>
<text x="370" y="1097" text-anchor="middle" class="node-title">核心指标</text>
<text x="370" y="1122" text-anchor="middle" class="node-sub">机架kW、PUE、良率、漏液率</text>
<rect x="515" y="1070" width="230" height="62" class="red box"/>
<text x="630" y="1097" text-anchor="middle" class="node-title">风险约束</text>
<text x="630" y="1122" text-anchor="middle" class="node-sub">CAPEX节奏、价格、可靠性事故</text>

<rect x="975" y="130" width="330" height="405" class="side"/>
<text x="1005" y="168" class="layer">相邻基础设施</text>
<text x="1015" y="215" class="node-title">电力链</text>
<text x="1015" y="242" class="node-sub">UPS、配电、母线、电源模块</text>
<text x="1015" y="292" class="node-title">网络与光模块</text>
<text x="1015" y="319" class="node-sub">800G/1.6T互连、交换机/NIC</text>
<text x="1015" y="369" class="node-title">储能与调峰</text>
<text x="1015" y="396" class="node-sub">园区电力容量与峰谷优化</text>
<text x="1015" y="446" class="node-title">IDC开发运营</text>
<text x="1015" y="473" class="node-sub">客户验证、交付能力、运维服务</text>

<rect x="975" y="610" width="330" height="300" class="commodity"/>
<text x="1005" y="648" class="layer">商品背景与待验证链路</text>
<text x="1015" y="695" class="node-title">铜、铝、不锈钢</text>
<text x="1015" y="722" class="node-sub">成本弹性存在，但差异化弱</text>
<text x="1015" y="772" class="node-title">氟化液/电子化学品</text>
<text x="1015" y="799" class="node-sub">浸没式相关度高，冷板主线较弱</text>
<text x="1015" y="849" class="node-title">软管/密封件</text>
<text x="1015" y="876" class="node-sub">需验证服务器客户与料号</text>

<path d="M500 420 L500 505" stroke="#2563eb" stroke-width="3" fill="none" marker-end="url(#arrow-blue)"/>
<path d="M500 810 L500 890" stroke="#2563eb" stroke-width="3" fill="none" marker-end="url(#arrow-blue)"/>
<path d="M920 340 C990 340 1000 340 1040 340" stroke="#9333ea" stroke-width="2.5" fill="none" stroke-dasharray="8 6" marker-end="url(#arrow-purple)"/>
<path d="M920 700 C990 700 1000 735 1040 735" stroke="#dc2626" stroke-width="2.5" fill="none" stroke-dasharray="8 6" marker-end="url(#arrow-red)"/>
<path d="M235 277 L235 575" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)"/>
<path d="M505 277 L505 575" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)"/>
<path d="M770 277 L770 575" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)"/>

<rect x="80" y="1255" width="1225" height="430" class="box"/>
<text x="110" y="1295" class="layer">A股映射：按直接暴露排序</text>
<rect x="120" y="1325" width="240" height="88" class="blue box"/>
<text x="240" y="1357" text-anchor="middle" class="node-title">核心系统商</text>
<text x="240" y="1384" text-anchor="middle" class="node-sub">英维克、申菱环境、高澜股份</text>
<rect x="395" y="1325" width="240" height="88" class="green box"/>
<text x="515" y="1357" text-anchor="middle" class="node-title">温控设备/冷源</text>
<text x="515" y="1384" text-anchor="middle" class="node-sub">同飞股份、佳力图、科华数据</text>
<rect x="670" y="1325" width="240" height="88" class="orange box"/>
<text x="790" y="1357" text-anchor="middle" class="node-title">材料与部件</text>
<text x="790" y="1384" text-anchor="middle" class="node-sub">飞荣达、科创新源、川环科技</text>
<rect x="945" y="1325" width="240" height="88" class="purple box"/>
<text x="1065" y="1357" text-anchor="middle" class="node-title">测试/整机/运营</text>
<text x="1065" y="1384" text-anchor="middle" class="node-sub">强瑞技术、浪潮信息、润泽科技</text>
<path d="M240 1413 L240 1480 L515 1480" stroke="#2563eb" stroke-width="2" fill="none" marker-end="url(#arrow-blue)"/>
<path d="M515 1413 L515 1480 L790 1480" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)"/>
<path d="M790 1413 L790 1480 L1065 1480" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)"/>
<text x="120" y="1535" class="node-title">读图方法</text>
<text x="120" y="1570" class="node-sub">主链看冷板/CDU/系统集成的客户认证和规模交付；上游看泵阀、快接、密封、TIM、冷却液的可靠性。</text>
<text x="120" y="1600" class="node-sub">相邻链路受同一AI算力资本开支拉动，但不应替代液冷服务器主链排序。</text>
<text x="120" y="1630" class="node-sub">商品背景输入只有在价格、国产替代或客户认证形成约束时，才进入核心投资线索。</text>

<g transform="translate(90,1740)">
  <line x1="0" y1="8" x2="40" y2="8" stroke="#2563eb" stroke-width="3" marker-end="url(#arrow-blue)"/>
  <text x="55" y="14" class="small">主链传导</text>
  <line x1="180" y1="8" x2="220" y2="8" stroke="#16a34a" stroke-width="3" marker-end="url(#arrow-green)"/>
  <text x="235" y="14" class="small">关键上游输入</text>
  <line x1="390" y1="8" x2="430" y2="8" stroke="#9333ea" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#arrow-purple)"/>
  <text x="445" y="14" class="small">相邻基础设施</text>
  <line x1="630" y1="8" x2="670" y2="8" stroke="#dc2626" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#arrow-red)"/>
  <text x="685" y="14" class="small">约束/待验证</text>
</g>
</svg>
"""


REPORT = """# 液冷服务器上下游产业链与A股公司分析报告

> 分析日期：2026-06-24  
> 研究范围：中国A股映射 + 全球AI服务器液冷技术路线；重点为AI数据中心冷板式液冷，兼顾浸没式/喷淋式与机房冷源。  
> 分析口径：以服务器/机柜液冷系统为主链，区分上游材料部件、中游液冷系统、下游服务器与AIDC运营，以及电力/光模块/IDC等相邻基础设施。

## 0. 核心结论

1. 液冷服务器的核心价值来自AI机架功耗密度提升后的散热约束解除：NVIDIA GB200/GB300 NVL72均是机架级液冷架构，Vera Rubin亦明确兼容液冷MGX服务器，说明液冷正从“节能选项”转为高密度AI服务器的交付前提。
2. 当前主线不是泛机房空调，而是冷板、CDU、Manifold/快接、泵阀传感、冷却液、气密/热循环测试和工程运维组成的系统能力。价值和瓶颈主要集中在客户验证、可靠性、交付规模、漏液风险控制和整机协同设计。
3. A股直接受益机会优先看已披露数据中心/工业温控/液冷产品的公司：英维克、申菱环境、高澜股份、同飞股份偏系统和冷源，飞荣达、科创新源、强瑞技术偏材料/部件/测试，浪潮信息、润泽科技、科华数据属于下游或相邻基础设施映射。
4. 上游不能只写“设备制造”。需要拆到铜/铝/不锈钢冷板、泵阀、快接头、EPDM/FKM/PTFE密封软管、TIM导热材料、乙二醇/去离子水/氟化液、传感器、过滤器、气密检漏和机房冷源；其中直接卡脖子更多在可靠性验证和工程交付，而非单一大宗原料。
5. 投资弹性取决于三类不确定：AI服务器资本开支是否持续上修、液冷渗透率与单机柜价值量是否提升、核心客户认证是否能转化为订单和收入。风险主要来自估值透支、价格竞争、客户集中、液冷事故和技术路线切换。

## 1. 研究对象、边界与口径

| 项目 | 定义 |
| --- | --- |
| 分析对象 | 液冷服务器产业链，重点为AI服务器/高密度机柜的冷板式液冷系统 |
| 纳入主线 | 冷板、CDU、Manifold、快接头、泵阀、传感器、管路密封、冷却液、换热器、机柜液冷、服务器整机协同、AIDC运维 |
| 相邻链路 | 电力UPS/配电、光模块/交换机、高速连接器、IDC建设、储能调峰、传统精密空调 |
| 弱相关/排除 | 仅有“算力/液冷概念”但无主营或产品证据的公司；普通家用/商用空调；与服务器液冷无直接传导的大宗商品 |
| 核心指标 | 单机柜功率、PUE、CDU容量、冷板良率、漏液率、客户认证、订单交付、数据中心CAPEX、液冷渗透率 |
| A股映射口径 | 优先使用主营业务、公告/年报、产品线和当前行情快照；未披露业务占比时标注“未披露；仅确认业务涉及” |

## 2. 行业背景与需求驱动

NVIDIA官方资料显示，GB200 NVL72将36个Grace CPU和72个Blackwell GPU连接在机架级液冷设计中；GB300 NVL72是全液冷机架级架构；Vera Rubin页面也强调兼容液冷NVIDIA MGX模块化服务器。这些信息共同指向一个产业变化：AI服务器从单机散热走向机柜/集群级热管理，散热、供电、网络、运维必须前置协同。

| 驱动 | 方向 | 影响环节 | 传导逻辑 | 证据强度 |
| --- | --- | --- | --- | --- |
| AI机架功耗密度提升 | 正向 | 冷板、CDU、Manifold、冷源 | GPU集群功率密度提升，传统风冷难以覆盖高热流密度，液冷成为高端AI机架交付条件 | 高 |
| 绿色数据中心能效约束 | 正向 | 液冷系统、自然冷却、余热回收 | PUE和能耗约束强化液冷、冷源优化、智能控制价值 | 中高 |
| 云厂商/AIDC资本开支 | 正向但周期 | 服务器整机、液冷系统、IDC工程 | 订单由AI服务器建设节奏驱动，液冷公司收入确认与机房交付周期相关 | 中高 |
| 国产化和客户验证 | 正向但分化 | CDU、冷板、泵阀、快接、材料 | 核心客户认证会放大头部供应商份额，弱验证公司容易停留在概念层 | 中 |
| 浸没式/喷淋式路线 | 中长期 | 冷却液、兼容材料、运维 | 更高热流密度场景可能打开冷却液和材料价值，但当前AI服务器主线仍以冷板式为主 | 中 |

## 3. 产业链全景图谱

![产业链图谱](assets/liquid-cooling-server-chain.png)

| 环节 | 细分领域 | 角色 | 关键输入 | 关键输出 | 价值/成本驱动 | 代表A股公司 |
| --- | --- | --- | --- | --- | --- | --- |
| 上游资源/材料 | 铜、铝、不锈钢、工程塑料、橡胶、氟化工、乙二醇、去离子水 | 提供冷板、管路、密封和冷却液基础材料 | 金属、化工品、橡胶/氟材料 | 冷板、软管、密封圈、冷却液 | 纯度、耐腐蚀、成本、稳定供应 | 飞荣达、科创新源、川环科技；氟化工需再核验 |
| 上游核心部件 | 冷板、泵、阀、快接头、Manifold、传感器、过滤器 | 决定流量、压降、漏液风险和维护便利性 | 材料、机加工、精密装配 | 机柜液冷BOM | 可靠性、冗余、客户认证、良率 | 英维克、高澜股份、申菱环境、同飞股份 |
| 中游系统 | CDU、冷板式液冷机柜、冷源模块、浸没式槽体/喷淋系统 | 将服务器热量传导到机房冷源 | 冷板、泵阀、控制器、换热器 | 可交付液冷系统 | 设计能力、工程经验、规模交付 | 英维克、申菱环境、高澜股份、同飞股份、佳力图 |
| 下游整机 | AI服务器、GPU机柜、NVL/Rack级系统 | 服务器设计阶段即绑定液冷方案 | GPU/CPU/电源/网络/结构件 | 高密度算力产品 | 客户订单、系统集成、可靠性 | 浪潮信息、工业富联等 |
| 下游运营 | AIDC、云厂商、智算中心、IDC工程 | 形成最终采购和运维需求 | 电力、土地、网络、服务器 | 算力服务和IDC收入 | PUE、运维成本、客户负载 | 润泽科技、科华数据、数据港等 |
| 相邻基础设施 | UPS/配电、光模块、交换机、储能、电力工程 | 与液冷服务器同受AI集群建设拉动 | 电源、网络、工程服务 | 高密度机房基础设施 | CAPEX强度、交付节奏 | 科华数据、沪电股份、光模块链公司 |

主链阅读顺序是“材料/部件 -> CDU/冷板系统 -> 服务器/机柜 -> AIDC运营”。电力、光模块、IDC运营是相邻链路，受同一AI算力资本开支驱动，但不能替代液冷服务器主链排序。

## 4. 上游材料、部件与制程要素挖掘

| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | 冷板、CDU、Manifold、快接头、泵、阀、传感器、过滤器 | 决定液冷系统的散热能力、漏液风险、维护便利性和冗余安全 | 高；客户认证和可靠性是核心稀缺 | High | 英维克、申菱环境、高澜股份、同飞股份、强瑞技术 | Core |
| Product BOM | TIM导热材料、导热垫片、均热/散热结构件、金属冷板 | 影响芯片到冷板的热阻和长期可靠性 | 中高；需材料一致性和客户验证 | Medium | 飞荣达、中石科技、科创新源 | Important |
| Manufacturing Process | 钎焊、机加工、表面处理、气密检漏、热循环测试、腐蚀测试 | 决定冷板、管路和CDU的良率与生命周期安全 | 高；工艺窗口和测试能力难以短期复制 | High | 强瑞技术、英维克、申菱环境、高澜股份 | Core/Important |
| Board/Package Materials | 密封圈、软管、工程塑料、PTFE/PPS/EPDM/FKM、连接器护套 | 支撑快接、管路和机柜布液系统的耐压、耐腐蚀、低析出 | 中；直接料号和客户认证需核验 | Medium | 科创新源、川环科技、沃尔核材 | Important/待验证 |
| Resource/feedstock | 铜、铝、不锈钢、乙二醇、氟化液、去离子水、缓蚀剂 | 影响冷板、换热器、冷却液和浸没式路线成本 | 分化；大宗材料差异化弱，氟化液/缓蚀配方更关键 | Medium/Low | 巨化股份、三美股份等氟化工候选需按产品核验 | Commodity/Important |
| Adjacent infrastructure | UPS/配电、光模块、交换机、IDC工程、储能调峰 | AI数据中心同源扩张，但不是液冷设备本体 | 高；与服务器液冷共同受益 | Medium | 科华数据、润泽科技、浪潮信息、光模块链公司 | Adjacent |

五层扫描结论：冷板/CDU/泵阀/快接/控制系统是核心；TIM、密封、软管、气密测试和冷却液是重要上游；铜铝不锈钢更多是商品背景，只有价格和供应扰动明显时才进入投资主线；氟化液主要对应浸没式路线，短期对冷板式主线的直接度低于CDU和冷板。

## 5. 产业链核心环节价值分布

| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 核心设备 | CDU、冷源模块、液冷门、水力模块 | 定性高；液冷系统中价值池核心 | 泵/板换/控制冗余、能效、稳定运行、工程交付 | High | 英维克、申菱环境、高澜股份、同飞股份 | 核心环节龙头/关键挑战者 | 主营与产品线确认，具体数据中心液冷收入占比多未披露 |
| 服务器端组件 | 冷板、Manifold、快接头、管路 | 定性高；直接贴近GPU/CPU热源 | 低热阻、低压降、漏液隔离、盲插快接、材料兼容 | High | 英维克、高澜股份、申菱环境、飞荣达 | 核心/重要配套 | 需客户认证和订单验证 |
| 材料与密封 | TIM、O形圈、软管、工程塑料、冷却液 | 中；单项价值不高但可靠性关键 | 耐腐蚀、低析出、绝缘/阻燃、长期稳定性 | Medium | 飞荣达、科创新源、川环科技、沃尔核材 | 重要配套/待验证 | 多数公司未披露服务器液冷收入占比 |
| 测试与制造工艺 | 气密检漏、热循环、可靠性测试、自动化治具 | 中高；量产良率和事故成本决定隐性价值 | 测试方法、工装、客户规范、批量一致性 | Medium/High | 强瑞技术 | 关键技术配套 | 主营文本显示液冷机柜测试设备、液冷服务器相关设备 |
| 整机与运营 | AI服务器、智算中心、IDC运维 | 总收入高，但液冷只是系统能力之一 | 整机协同、客户订单、电力/机房资源 | Medium | 浪潮信息、润泽科技、科华数据 | 下游核心/相邻受益 | 直接液冷设备收入不应简单等同 |
| 替代路线 | 浸没式、喷淋式、两相冷却 | 中长期潜在高价值 | 冷却液兼容性、维护标准、材料可靠性 | Medium | 氟化工/温控公司待验证 | 观察名单 | 当前AI服务器主线仍偏冷板式 |

价值分布的核心判断是：设备系统商比单一材料商更直接承接AI服务器液冷订单；但长期壁垒并不只在“会做设备”，而在冷板/CDU/管路/控制/测试/运维的一体化验证。材料公司若不能证明服务器客户、料号和收入贡献，应放在重要配套或待验证层级。

## 6. 竞争格局与核心壁垒

| 环节/细分 | 全球领导者/参考体系 | 中国/A股映射 | 壁垒类型 | 国产化状态 | 核心瓶颈 |
| --- | --- | --- | --- | --- | --- |
| 机架级液冷系统 | NVIDIA生态、服务器OEM/ODM与国际热管理厂商 | 英维克、申菱环境、高澜股份、同飞股份 | 系统设计、客户验证、规模交付 | 国产供应商加速进入 | 客户认证、可靠性、交付一致性 |
| 冷板/快接/管路 | 国际快接与热管理厂商 | 英维克、飞荣达、科创新源、川环科技等 | 精密加工、材料兼容、漏液控制 | 部分国产替代 | 料号认证、寿命验证、事故责任 |
| CDU/冷源 | 国际制冷/热管理厂商 | 英维克、申菱环境、高澜股份、同飞股份、佳力图 | 泵阀控制、换热效率、冗余、运维 | 国产竞争充分但分化 | 大客户订单与项目经验 |
| 冷却液/氟化液 | 国际化学材料公司 | 巨化股份、三美股份等候选需核验 | 配方、兼容性、环保合规、成本 | 冷板式主线需求有限 | 浸没式渗透率和客户标准 |
| 测试与运维 | 服务器OEM规范和第三方测试 | 强瑞技术、系统商自建能力 | 检漏、热循环、自动化、现场运维 | 国产配套逐步完善 | 工艺标准化和批量交付 |

竞争格局呈现“系统商先受益、材料部件分化、下游运营商验证需求”的结构。英维克、申菱环境、高澜股份、同飞股份更接近液冷系统主线；飞荣达、科创新源、川环科技需看是否从传统热管理/汽车管路迁移到服务器液冷客户；强瑞技术的液冷测试设备更偏制造和可靠性配套。

## 7. A股公司映射与核心地位判断

| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 英维克 | 002837 | 中游系统 | 数据中心/机房精密温控、液冷系统 | 未披露；主营为精密温控节能解决方案，机房温控为核心产品类型 | 机房温控、机柜温控、电子散热、数据中心微模块 | High | 核心环节龙头 | 主营业务覆盖机房温控、电子散热和数据中心系统，直接度最高之一 |
| 申菱环境 | 301018 | 中游系统 | 数据中心液冷冷源、液冷门、水力模块 | 未披露；数据服务板块含一体化冷源、干冷器、液冷门、冷源模块、水力模块 | 特种空调、冷源模块、液冷门、相变系列 | High | 核心挑战者 | 主营文本显示数据服务板块产品直接进入液冷机房链条 |
| 高澜股份 | 300499 | 中游系统 | 工业热管理、数据中心液冷 | 未披露；产品名称包含数据中心液冷产品 | 纯水冷却、工业热管理、大功率装置热管理 | High | 关键技术突破者 | 工业液冷积累可迁移到数据中心，需跟踪数据中心订单占比 |
| 同飞股份 | 300990 | 中游设备 | 工业温控、液体恒温设备、纯水冷却单元 | 未披露；主营为工业温控设备 | 液体恒温设备、纯水冷却单元、特种换热器 | Medium/High | 重要配套/挑战者 | 工业温控能力相关，服务器液冷收入弹性需进一步验证 |
| 飞荣达 | 300602 | 上游材料/部件 | 热管理材料与结构件 | 未披露；主营含网络通信、存储及服务器相关热管理材料及器件 | 导热材料、散热结构件、电磁屏蔽/热管理组件 | Medium | 重要配套 | 与服务器热管理链条相关，需验证液冷冷板/客户料号 |
| 科创新源 | 300731 | 上游材料/密封 | 高分子材料、热管理系统、散热金属结构件 | 未披露；主营含热管理系统产品、防水密封/绝缘材料 | 密封材料、散热金属结构件、绝缘防火材料 | Medium | 重要配套/待验证 | 与管路密封和热管理相关，服务器液冷直接订单需核验 |
| 强瑞技术 | 301128 | 制造测试 | 液冷机柜测试设备、液冷服务器测试相关设备 | 未披露；主营文本列示液冷机柜测试设备和液冷服务器相关设备 | 自动化测试设备、治具、液冷散热器、检漏/测试设备 | Medium/High | 关键技术配套 | 直接进入液冷可靠性测试链条，弹性取决于客户扩产 |
| 川环科技 | 300547 | 上游管路 | 橡塑软管及总成 | 未披露；主营为汽车冷却系统软管，服务器液冷迁移待验证 | 冷却系统软管、橡塑密封件 | Low/Medium | 待验证配套 | 管路能力相关，但数据中心客户和产品占比需核验 |
| 佳力图 | 603912 | 中游/相邻 | 数据机房精密环境控制 | 未披露；主营为数据机房精密环境控制设备 | 精密空调、机房环境一体化产品 | Low/Medium | 间接/传统温控 | 传统机房温控基础好，但液冷服务器主线暴露需订单证明 |
| 浪潮信息 | 000977 | 下游整机 | AI服务器、存储、交换类产品 | 未披露；服务器为核心产品类型 | 服务器产品、存储类、交换类等 | Medium | 下游核心整机商 | 液冷系统需求的传导端，非液冷设备供应商 |
| 润泽科技 | 300442 | 下游运营 | IDC/AIDC运营 | 未披露；主营为IDC业务和AIDC业务 | AIDC、数据处理和存储支持 | Low/Medium | 相邻受益 | 液冷采购方/运营端映射，非设备主链 |
| 科华数据 | 002335 | 相邻基础设施 | 数据中心产品、智慧电能、IDC服务 | 未披露；数据中心产品和IDC服务相关 | UPS/电力、数据中心产品、IDC服务 | Low/Medium | 相邻基础设施 | 与液冷服务器同受高密度机房建设驱动，但不是液冷核心设备 |

直接受益排序上，英维克、申菱环境、高澜股份、同飞股份更靠近液冷系统收入；强瑞技术和飞荣达属于可靠性测试与热管理材料配套；浪潮信息、润泽科技、科华数据是需求端或相邻基础设施。川环科技、科创新源等材料/管路公司需要用客户认证、料号、收入占比进一步提高置信度。

## 8. 投资线索、交易跟踪与目标价情景

| 公司 | 代码 | 产业链结论 | 财务质量 | 当前估值 | 技术面/趋势 | 买点区间 | 止损/失效条件 | 目标价/空间 | 综合判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 英维克 | 002837 | 核心液冷系统商，直接受益但估值敏感 | 毛利率约24.3%，净利率约1.2%，需看订单兑现 | 动态PE口径很高，PB约32；估值已充分反映预期 | 当日上涨约1.69%，换手率约9.31%，活跃但波动大 | 不追高；回踩放量不破中期均线后观察 | 跌破放量平台或订单低于预期 | 情景目标需以订单/利润上修重估，当前不宜机械给高倍数 | 核心观察，偏趋势票 |
| 申菱环境 | 301018 | 数据中心液冷冷源/液冷门直接度高 | 毛利率约20.6%，净利率约5.1% | 动态PE较高，PB约15.6 | 当日上涨约2.14%，换手率约7.05% | 回调至前期平台且成交缩量时观察 | 高位放量长阴或大客户验证不及预期 | 看订单兑现和毛利修复空间 | 核心挑战者，估值约束强 |
| 高澜股份 | 300499 | 工业热管理迁移到数据中心液冷，弹性较高 | 毛利率约30.7%，净利率约8.2% | 动态PE约214，PB约9.45 | 当日上涨约3.74%，换手率约19.1%，资金博弈强 | 高换手后等待缩量回踩 | 跌破主题启动区或订单证伪 | 若数据中心液冷收入占比提升，有估值弹性 | 高弹性观察 |
| 同飞股份 | 300990 | 工业温控/纯水冷却单元，重要配套 | 数据不足；需补年报分部口径 | 行情快照显示热度高 | 当日上涨约9.36%，换手率约12.44% | 等待连续大涨后的回踩确认 | 量价背离、订单未兑现 | 空间取决于液冷业务收入占比 | 观察名单，避免追涨 |
| 飞荣达 | 300602 | 热管理材料和结构件，受益于服务器热管理升级 | 毛利率约20.9%，净利率约4.8% | 动态PE约92.5，PB约6.96 | 当日上涨约6.82%，换手率约6.74% | 回踩确认服务器液冷订单后再评估 | 无法证明液冷料号或客户 | 以材料单机价值和客户放量评估 | 重要配套 |
| 强瑞技术 | 301128 | 液冷机柜/服务器测试设备，可靠性配套稀缺 | 毛利率约32.1%，净利率约6.3% | 动态PE约378，PB约26；估值很高 | 当日下跌约2.04%，换手率约5.72% | 等待估值消化和订单公告 | 测试设备需求不及预期 | 空间取决于液冷测试设备订单规模 | 高估值高弹性观察 |

交易跟踪口径来自2026-06-24公开行情快照和主营业务采样，仅用于建立观察框架。若需要正式买点、目标价和止损，应进一步调用财报拆分、历史K线和一致预期数据；当前报告不把概念热度等同于买入建议。

## 9. 催化因素与产业传导路径

| 催化因素 | 影响链路 | 传导路径 | 受益公司 | 观察指标 |
| --- | --- | --- | --- | --- |
| NVIDIA GB300/Rubin机架级系统放量 | 冷板、CDU、服务器整机 | 高功率机柜需求提升 -> 液冷系统前置设计 -> 订单和交付收入 | 英维克、申菱环境、高澜股份、浪潮信息 | AI服务器订单、客户认证、液冷机柜交付 |
| 国内AIDC建设提速 | 液冷设备、冷源、IDC工程 | 算力园区CAPEX -> 高密度机房 -> 液冷系统采购 | 英维克、申菱环境、润泽科技、科华数据 | AIDC项目开工、PUE指标、单机柜功率 |
| 液冷标准化与客户认证 | 快接、管路、检测、运维 | 标准收敛 -> 供应商规模化 -> 头部集中 | 强瑞技术、飞荣达、科创新源 | 料号认证、订单公告、良率/漏液率 |
| 浸没式路线试点扩大 | 冷却液、材料兼容、运维 | 更高热流密度场景 -> 冷却液和兼容材料需求 | 氟化工候选、温控系统商 | 浸没式项目数量、冷却液成本、环保规范 |
| 传统风冷转液冷 | 传统温控公司转型 | 精密空调能力 -> 液冷冷源和工程能力 | 佳力图、申菱环境、英维克 | 液冷产品收入占比、毛利率变化 |

## 10. 风险提示

1. 需求风险：AI服务器CAPEX若降速，液冷订单会随整机交付周期波动。
2. 技术路线风险：冷板式、浸没式、喷淋式、风液混合路线的价值分配不同，押错路线会影响材料和设备公司弹性。
3. 可靠性风险：漏液、腐蚀、结垢、冷却液兼容性和现场维护事故会放大客户验证门槛。
4. 估值风险：多家公司动态估值已包含高增长预期，若订单或利润确认慢于股价，回撤空间较大。
5. 证据风险：部分材料/管路公司尚未披露服务器液冷收入占比，不能仅凭概念标签进入核心排序。
6. 竞争风险：系统商可能从设备销售转向价格竞争，整机厂和海外热管理厂商也可能压缩中游利润。

## 11. 数据来源、证据强度与待核验事项

| 结论/数据 | 来源 | 日期 | 置信度 |
| --- | --- | --- | --- |
| GB200 NVL72为机架级液冷设计，包含36 Grace CPU和72 Blackwell GPU | NVIDIA GB200 NVL72官方页面 | 2026-06-24访问 | High |
| GB300 NVL72为全液冷机架级架构，集成72 Blackwell Ultra GPU和36 Grace CPU | NVIDIA GB300 NVL72官方页面 | 2026-06-24访问 | High |
| Vera Rubin页面披露兼容液冷NVIDIA MGX模块化服务器 | NVIDIA Vera Rubin NVL72官方页面 | 2026-06-24访问 | High |
| 英维克主营包括机房温控、机柜温控、电子散热和数据中心系统 | 公司主营业务与2025年年度报告公告 | 2026-04-21/2026-06-24采样 | High |
| 高澜股份主营包括数据中心液冷产品和工业热管理 | 公司主营业务与2025年年度报告公告 | 2026-04-24/2026-06-24采样 | High |
| 申菱环境数据服务板块含一体化冷源、干冷器、液冷门、冷源模块、水力模块 | 公司主营业务与2025年年度报告公告 | 2026-04-27/2026-06-24采样 | High |
| 同飞股份主营为工业温控设备，产品含液体恒温设备、纯水冷却单元 | 公司主营业务与2025年年度报告公告 | 2026-04-01/2026-06-24采样 | High |
| 飞荣达主营覆盖服务器相关热管理材料及器件 | 公司主营业务与2025年年度报告公告 | 2026-04-28/2026-06-24采样 | High |
| 强瑞技术主营文本列示液冷机柜测试设备和液冷服务器相关设备 | 公司主营业务与2025年年度报告公告 | 2026-04-16/2026-06-24采样 | High |
| A股行情、动态PE/PB、毛利率/净利率为公开行情快照口径 | 东方财富公开行情快照工具 | 2026-06-24 | Medium |

待核验事项：第一，液冷业务分部收入和大客户订单仍需逐家公司从年报、投资者关系记录和订单公告中精读；第二，冷板/快接/软管/TIM材料的客户料号和认证状态需要用公告或调研纪要确认；第三，浸没式冷却液相关A股公司目前更适合作为路线观察，不宜直接纳入冷板式液冷服务器核心排序。
"""


SOURCE_DATA = {
    "topic": "liquid-cooling-server-chain-analysis",
    "generated_at": "2026-06-24T00:00:00+08:00",
    "notes": [
        "Reader-facing report uses relative image paths only.",
        "Runtime adapter diagnostics are intentionally kept out of report.md.",
    ],
    "sources": [
        {"tool": "web", "function_or_path": "https://www.nvidia.com/en-us/data-center/gb200-nvl72/", "subject": "GB200 NVL72 official page", "status": "ok", "rows": None, "error": None, "confidence": "High"},
        {"tool": "web", "function_or_path": "https://www.nvidia.com/en-us/data-center/gb300-nvl72/", "subject": "GB300 NVL72 official page", "status": "ok", "rows": None, "error": None, "confidence": "High"},
        {"tool": "web", "function_or_path": "https://www.nvidia.com/en-us/data-center/vera-rubin-nvl72/", "subject": "Vera Rubin NVL72 official page", "status": "ok", "rows": None, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "002837 英维克", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "300499 高澜股份", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "301018 申菱环境", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "300990 同飞股份", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "300602 飞荣达", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "300731 科创新源", "status": "ok", "rows": 3, "error": None, "confidence": "High"},
        {"tool": "filing", "function_or_path": "CNINFO 2025 annual report", "subject": "301128 强瑞技术", "status": "ok", "rows": 2, "error": None, "confidence": "High"},
        {"tool": "akshare", "function_or_path": "main business text", "subject": "002837/300499/301018/300990/300602/300731/301128/000977", "status": "ok", "rows": 8, "error": None, "confidence": "Medium"},
        {"tool": "efinance", "function_or_path": "quote snapshot", "subject": "shortlisted A-share quotes", "status": "ok", "rows": 12, "error": None, "confidence": "Medium"},
        {"tool": "efinance", "function_or_path": "base info", "subject": "shortlisted A-share valuation/financial snapshot", "status": "ok", "rows": 12, "error": None, "confidence": "Medium"},
        {"tool": "akshare", "function_or_path": "cninfo profile", "subject": "shortlisted A-share company profiles", "status": "ok", "rows": 12, "error": None, "confidence": "Medium"},
        {"tool": "web", "function_or_path": "policy/industry public materials", "subject": "green data center and liquid cooling policy direction", "status": "fallback", "rows": None, "error": None, "confidence": "Medium"},
    ],
}


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "liquid-cooling-server-chain.svg").write_text(SVG, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=SVG.encode("utf-8"),
        write_to=str(ASSET_DIR / "liquid-cooling-server-chain.png"),
        output_width=1800,
    )
    (OUT_DIR / "report.md").write_text(REPORT, encoding="utf-8")
    (OUT_DIR / "source_data.json").write_text(
        json.dumps(SOURCE_DATA, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
