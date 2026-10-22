"""Insert user-provided founder and a transparent six-month funding scenario."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'web/pitch/deck.json'
deck = json.loads(path.read_text(encoding='utf-8'))
slides = deck['slides']
assert len(slides) == 18, 'Plan already inserted'
for slide in slides:
    if slide['kind'] == 'team':
        slide['big'] = 'Mr. Supakrit Wapakpetch\nand AI Team'
        slide['subtitle'] = 'Founder-led engineering · MIT open core · reproducible research'
        slide['notes'] = 'ชื่อทีมระบุโดยผู้ก่อตั้ง: Mr. Supakrit Wapakpetch and AI Team ไม่อ้างประวัติการศึกษา จำนวนพนักงาน หรือประสบการณ์ที่ยังไม่ได้ให้ข้อมูล ผลงานที่ตรวจได้คือโค้ดและผลทดลอง'
        slide['sources'].append('Founder identity supplied by the user, 23 October 2026')
    if slide['kind'] == 'ask':
        slide['title'] = '$240k for six months of execution'
        slide['subtitle'] = 'Build the multi-host product. Validate paid demand.'
        slide['items'] = [['Technical gate', 'Two-host recovery, then a controlled ten-host pilot'],
                          ['Commercial gate', '10 paid sites base case; 18 sites for lean operating profit']]
        slide['takeaway'] = 'Proposed raise and scenarios; 18 sites is a stretch target. Terms and valuation remain open.'
        slide['notes'] = 'ขอทุนที่เสนอ240,000ดอลลาร์ runway6เดือน:operatingbudget204,000และcontingency36,000 เป้าฐาน10sitesยังขาดทุน18sitesเป็นstretchที่เริ่มบวกหลังลดfixedcostเหลือ24,000ต่อเดือน ไม่อ้างว่าทำได้แน่นอนและไม่คำนวณvaluationจากmarketcapบริษัทใหญ่'
        slide['sources'] += ['web/pitch/financial-plan.json', 'web/pitch/funding-plan.md']

market = {'kind':'market-context','light':True,'title':'Global spending supports a focused local wedge',
          'metrics':[['$500B','cloud infrastructure revenue','Trailing 12 months to Q2 2026; Synergy estimate'],
                     ['$5.124T','NVIDIA equity market cap','Live-source snapshot accessed 23 Oct 2026'],
                     ['18 sites','lean profit threshold','Our operating scenario; demand unvalidated']],
          'takeaway':'Spending sizes demand context; public market cap is a valuation reference. PASADHI addressable demand needs validation.',
          'notes':'ตลาดคลาวด์500Bเป็นรายได้12เดือนตามSynergy ไม่ใช่TAMของPASADHIทั้งหมด มูลค่าหุ้นNVIDIA5.124Tเป็นsnapshotจากCompaniesMarketCapตรวจ23ต.ค.2026ซึ่งเปลี่ยนได้ ไม่ใช่เงินที่PASADHIเข้าถึงได้หรือvaluationที่เสนอ ทุน240kมาจากงบmilestone6เดือน ไม่ได้เอาเปอร์เซ็นต์marketcapมาคิดเป็นเงินระดมทุน',
          'sources':['https://www.srgresearch.com/articles/q2-cloud-market-passes-143-billion-highest-growth-rate-in-eight-years',
                     'https://companiesmarketcap.com/nvidia/marketcap/', 'web/pitch/financial-plan.json']}
slides.insert(7, market)
deck['coreCount'] = 14

budget = [
    {'use':'Engineering', 'amount':96000,'percent':40,'outcome':'Kernel, scheduler, two-host recovery; planned roles, not existing headcount'},
    {'use':'Pilot delivery + QA', 'amount':48000,'percent':20,'outcome':'Test hardware, rollout, workload benchmarks and recovery verification'},
    {'use':'Customer discovery + sales', 'amount':36000,'percent':15,'outcome':'Interviews, qualified pipeline and paid pilot conversion'},
    {'use':'Security + legal + operations', 'amount':24000,'percent':10,'outcome':'Data controls, contracts, IP and release operations'},
    {'use':'Contingency', 'amount':36000,'percent':15,'outcome':'15% buffer; release only against milestone review'}
]
price, variable, fixed = 44.28, 16.37, 24000
cases=[]
for name,sites in [('Downside',5),('Base',10),('Profit gate',18),('Expansion',25)]:
    nodes=sites*50
    revenue=round(nodes*price,2)
    cost=round(nodes*variable,2)
    cases.append({'name':name,'sites':sites,'nodes':nodes,'mrr':revenue,'direct_cost':cost,
                  'fixed_cost':fixed,'operating_profit':round(revenue-cost-fixed,2)})
plan={'status':'Founder planning proposal, not forecast or approved spend','runway_months':6,'raise_usd':240000,
      'operating_budget_usd':204000,'contingency_usd':36000,'monthly_operating_budget_usd':34000,
      'budget':budget,'price_per_node_month_usd':price,'direct_cost_per_node_month_usd':variable,
      'post_runway_fixed_cost_usd_month':fixed,'nodes_per_site':50,'break_even_nodes':860,
      'break_even_sites_rounded_up':18,'scenarios':cases,
      'broad_cloud_revenue_usd_ttm':500000000000,'market_source':market['sources'][0],
      'market_cap_snapshot_usd':5124000000000,'market_cap_source':market['sources'][1],
      'market_cap_accessed':'2026-10-23','usd_fx_local_per_usd':33.65,
      'profit_gate_arr_usd':cases[2]['mrr']*12,
      'profit_gate_share_of_broad_spending_percent':cases[2]['mrr']*12/500000000000*100,
      'assumptions':['No validated conversion rate or probability of success is available.',
                     'MRR requires active paying nodes; contracted backlog and pilots are not MRR.',
                     'A node cost is an inherited model allocation, not a supplier quote.',
                     'Month-seven fixed cost falls to $24k; this requires an explicit lean staffing/operations plan.',
                     'Operating profit excludes taxes, financing and exceptional costs.',
                     'Pilot fees are credited to year one and are not counted again as recurring revenue.',
                     'If the base case holds, follow-on funding, stronger sales or cost reductions are required.']}
assert sum(x['amount'] for x in budget)==240000
assert sum(x['percent'] for x in budget)==100
assert 859*(price-variable)<fixed<=860*(price-variable)
(ROOT/'web/pitch/financial-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
slides.extend([
 {'kind':'budget','light':True,'title':'Six-month use of funds: $240,000',
  'table':[['Use','Amount','Share']]+[[x['use'],f"${x['amount']:,}",f"{x['percent']}%"] for x in budget]+[['Total','$240,000','100%']],
  'takeaway':'$204k operating plan + $36k buffer; $34k/month planned operating spend before revenue',
  'notes':'งบเป็นข้อเสนอ4หมวดoperating204kพร้อมbuffer36k Engineering96kเทียบงบรวม16kต่อเดือนสำหรับงานระบบ;pilot48kสำหรับทดสอบและติดตั้ง;GTM36k;security/legal24k ต้องอัปเดตด้วยใบเสนอราคาและสัญญาจ้างก่อนใช้เงินจริง ไม่ใช่ราคาตลาดที่ตรวจยืนยันแล้ว',
  'sources':['web/pitch/financial-plan.json']},
 {'kind':'sensitivity','title':'Operating profit needs 18 paid sites',
  'table':[['Scenario','Sites / nodes','MRR','Profit / month']]+[[x['name'],f"{x['sites']} / {x['nodes']}",f"${x['mrr']:,.0f}",f"{'-' if x['operating_profit']<0 else ''}${abs(x['operating_profit']):,.0f}"] for x in cases],
  'takeaway':'50 paying nodes/site; $44.28 price; $16.37 direct cost; $24k fixed costs after month six. Scenarios, not forecast.',
  'notes':'สูตรกำไร=nodes×(44.28−16.37)−24,000 break-even860nodesหรือ18sitesที่50nodes/site ฐาน10sitesกำไรติดลบ10,045ต่อเดือน18sitesบวก1,119ต่อเดือน25sitesบวก10,888ต่อเดือน ตัวเลขกำไรดำเนินงานก่อนภาษีและค่าใช้จ่ายพิเศษ การลดfixedcostเดือน7เป็นเงื่อนไขสำคัญ ไม่มีหลักฐานความน่าจะเป็นของการได้ลูกค้าขนาดนี้',
  'sources':['web/pitch/financial-plan.json','paper/SOLUTION_FULL.md: node cost','docs/SALES_KIT.th.md: proposed price']},
 {'kind':'gates','light':True,'title':'Release capital against customer evidence',
  'items':[['Months 1–2','15 buyer interviews; two-host recovery; three design-partner targets'],
           ['Months 3–4','Two paid pilots targeted; verify workload ROI and support burden'],
           ['Months 5–6','Base target: 10 paid sites. Stretch: 18 sites and lean break-even']],
  'takeaway':'If paid demand misses the gates, slow hiring, narrow the workload and preserve the buffer before scaling',
  'notes':'ทั้ง15interviews,3designpartners,2paidpilots,10หรือ18sitesล้วนเป็นเป้าหมายที่เสนอ ไม่ใช่pipelineหรือสัญญาที่มีแล้ว หากไม่ผ่านเกณฑ์ให้ชะลอขยายทีมและลดscopeก่อนใช้contingency โมเดลนี้ไม่สามารถรับประกันกำไรสิ้นrunwayได้',
  'sources':['web/pitch/financial-plan.json','docs/ROADMAP.md']}
])
path.write_text(json.dumps(deck,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Updated founder, market context, $240k proposal and 6-month scenarios; {len(slides)} slides.')
